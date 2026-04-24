package handlers

import (
	"context"
	"net"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

type HealthHandler struct {
	db    *pgxpool.Pool
	rdb   *redis.Client
	kafka []string // broker addresses
}

func NewHealthHandler(db *pgxpool.Pool, rdb *redis.Client, kafkaBrokers []string) *HealthHandler {
	return &HealthHandler{db: db, rdb: rdb, kafka: kafkaBrokers}
}

func (h *HealthHandler) Handle(c *fiber.Ctx) error {
	ctx, cancel := context.WithTimeout(c.Context(), time.Second)
	defer cancel()

	checks := fiber.Map{}
	healthy := true

	// Postgres
	if err := h.db.Ping(ctx); err != nil {
		checks["postgres"] = "error: " + err.Error()
		healthy = false
	} else {
		checks["postgres"] = "ok"
	}

	// Redis
	if err := h.rdb.Ping(ctx).Err(); err != nil {
		checks["redis"] = "error: " + err.Error()
		healthy = false
	} else {
		checks["redis"] = "ok"
	}

	// Kafka — simple TCP dial to first broker
	if len(h.kafka) > 0 {
		conn, err := net.DialTimeout("tcp", h.kafka[0], time.Second)
		if err != nil {
			checks["kafka"] = "error: " + err.Error()
			healthy = false
		} else {
			conn.Close()
			checks["kafka"] = "ok"
		}
	}

	status := "ok"
	code := fiber.StatusOK
	if !healthy {
		status = "degraded"
		code = fiber.StatusServiceUnavailable
	}

	return c.Status(code).JSON(fiber.Map{
		"status": status,
		"checks": checks,
	})
}
