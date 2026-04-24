package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/ansrivas/fiberprometheus/v2"
	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/limiter"
	"github.com/joho/godotenv"
	"github.com/redis/go-redis/v9"

	"github.com/razorscope/webhook-receiver/internal/bloom"
	"github.com/razorscope/webhook-receiver/internal/config"
	"github.com/razorscope/webhook-receiver/internal/db"
	"github.com/razorscope/webhook-receiver/internal/handlers"
	kafkapkg "github.com/razorscope/webhook-receiver/internal/kafka"
	"github.com/razorscope/webhook-receiver/internal/middleware"
)

func main() {
	// Load .env in dev — ignored in prod (env vars already set)
	_ = godotenv.Load()

	cfg, err := config.Load()
	if err != nil {
		slog.Error("config load failed", "err", err)
		os.Exit(1)
	}

	setupLogger(cfg.LogLevel)

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	// PostgreSQL
	pool, err := db.NewPool(ctx, cfg.DatabaseURL)
	if err != nil {
		slog.Error("postgres init failed", "err", err)
		os.Exit(1)
	}
	defer pool.Close()
	slog.Info("postgres connected")

	// Redis
	rdb := redis.NewClient(&redis.Options{
		Addr:     cfg.RedisAddr,
		Password: cfg.RedisPassword,
	})
	if err := rdb.Ping(ctx).Err(); err != nil {
		slog.Error("redis ping failed", "err", err)
		os.Exit(1)
	}
	defer rdb.Close()
	slog.Info("redis connected")

	// Bloom filter — idempotent reserve
	bloom.EnsureFilter(ctx, rdb)

	// Kafka producer
	producer := kafkapkg.NewProducer(cfg.KafkaBrokers, cfg.KafkaTopic, cfg.KafkaWriteTimeout)
	defer func() {
		if err := producer.Close(); err != nil {
			slog.Warn("kafka producer close error", "err", err)
		}
	}()
	slog.Info("kafka producer ready", "brokers", cfg.KafkaBrokers, "topic", cfg.KafkaTopic)

	// Fallback drain loop — runs until shutdown
	go kafkapkg.StartDrainLoop(ctx, producer, rdb)

	// Fiber app
	app := fiber.New(fiber.Config{
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
		BodyLimit:    1 * 1024 * 1024, // 1 MB
		// Disable default error handler so we control response format
		ErrorHandler: func(c *fiber.Ctx, err error) error {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": err.Error()})
		},
	})

	app.Use(middleware.Logger())

	prom := fiberprometheus.New("webhook_receiver")
	prom.RegisterAt(app, "/metrics")
	app.Use(prom.Middleware)

	webhookLimiter := limiter.New(limiter.Config{
		Max:        100,
		Expiration: 1 * time.Minute,
		KeyGenerator: func(c *fiber.Ctx) string {
			return c.Params("merchantID")
		},
		LimitReached: func(c *fiber.Ctx) error {
			return c.Status(fiber.StatusTooManyRequests).JSON(fiber.Map{
				"error": "rate limit exceeded, retry after 60s",
			})
		},
	})

	webhookHandler := handlers.NewWebhookHandler(pool, rdb, producer, cfg.TimestampToleranceSec)
	healthHandler := handlers.NewHealthHandler(pool, rdb, cfg.KafkaBrokers)

	app.Post("/v1/webhooks/razorpay/:merchantID", webhookLimiter, webhookHandler.Handle)
	app.Get("/health", healthHandler.Handle)

	// Graceful shutdown
	go func() {
		<-ctx.Done()
		slog.Info("shutting down")
		_ = app.ShutdownWithTimeout(10 * time.Second)
	}()

	slog.Info("webhook receiver starting", "port", cfg.Port)
	if err := app.Listen(":" + cfg.Port); err != nil {
		slog.Error("server error", "err", err)
		os.Exit(1)
	}
}

func setupLogger(level string) {
	var l slog.Level
	switch level {
	case "debug":
		l = slog.LevelDebug
	case "warn":
		l = slog.LevelWarn
	case "error":
		l = slog.LevelError
	default:
		l = slog.LevelInfo
	}
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: l})))
}
