package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"
)

type Config struct {
	DatabaseURL          string
	RedisAddr            string
	RedisPassword        string
	KafkaBrokers         []string
	KafkaTopic           string
	KafkaWriteTimeout    time.Duration
	Port                 string
	TimestampToleranceSec int64
	LogLevel             string
}

func Load() (*Config, error) {
	cfg := &Config{
		DatabaseURL:          requireEnv("DATABASE_URL"),
		RedisAddr:            requireEnv("REDIS_ADDR"),
		RedisPassword:        os.Getenv("REDIS_PASSWORD"),
		KafkaTopic:           envOr("KAFKA_TOPIC", "razorpay.events"),
		Port:                 envOr("PORT", "8080"),
		LogLevel:             envOr("LOG_LEVEL", "info"),
	}

	brokers := requireEnv("KAFKA_BROKERS")
	cfg.KafkaBrokers = strings.Split(brokers, ",")

	writeTimeout, err := time.ParseDuration(envOr("KAFKA_WRITE_TIMEOUT", "2s"))
	if err != nil {
		return nil, fmt.Errorf("invalid KAFKA_WRITE_TIMEOUT: %w", err)
	}
	cfg.KafkaWriteTimeout = writeTimeout

	tolSec, err := strconv.ParseInt(envOr("TIMESTAMP_TOLERANCE_SEC", "300"), 10, 64)
	if err != nil {
		return nil, fmt.Errorf("invalid TIMESTAMP_TOLERANCE_SEC: %w", err)
	}
	cfg.TimestampToleranceSec = tolSec

	return cfg, nil
}

func requireEnv(key string) string {
	v := os.Getenv(key)
	if v == "" {
		panic(fmt.Sprintf("required environment variable %q is not set", key))
	}
	return v
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
