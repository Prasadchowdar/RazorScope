package db

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

func NewPool(ctx context.Context, dsn string) (*pgxpool.Pool, error) {
	cfg, err := pgxpool.ParseConfig(dsn)
	if err != nil {
		return nil, fmt.Errorf("parse postgres DSN: %w", err)
	}
	cfg.MaxConns = 10
	cfg.MinConns = 2
	cfg.MaxConnLifetime = 30 * time.Minute
	cfg.MaxConnIdleTime = 5 * time.Minute

	pool, err := pgxpool.NewWithConfig(ctx, cfg)
	if err != nil {
		return nil, fmt.Errorf("create postgres pool: %w", err)
	}

	pingCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	if err := pool.Ping(pingCtx); err != nil {
		return nil, fmt.Errorf("postgres ping: %w", err)
	}
	return pool, nil
}

// GetMerchantWebhookSecret fetches the webhook_secret for a merchant by ID.
// Returns ("", nil) if merchant not found — callers must treat that as 401.
func GetMerchantWebhookSecret(ctx context.Context, pool *pgxpool.Pool, merchantID string) (string, error) {
	var secret string
	err := pool.QueryRow(ctx,
		`SELECT webhook_secret FROM merchants WHERE id = $1 AND deleted_at IS NULL`,
		merchantID,
	).Scan(&secret)
	if err != nil {
		return "", err
	}
	return secret, nil
}

// RecordWebhookDelivery inserts a delivery record asynchronously (best-effort).
func RecordWebhookDelivery(ctx context.Context, pool *pgxpool.Pool, merchantID, eventID, eventType, status string, kafkaOffset *int64, errDetail string) {
	_, _ = pool.Exec(ctx,
		`INSERT INTO webhook_deliveries (merchant_id, event_id, event_type, status, kafka_offset, error_detail)
         VALUES ($1, $2, $3, $4, $5, NULLIF($6, ''))
         ON CONFLICT (merchant_id, event_id) DO UPDATE SET status = EXCLUDED.status, error_detail = EXCLUDED.error_detail`,
		merchantID, eventID, eventType, status, kafkaOffset, errDetail,
	)
}
