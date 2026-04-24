package kafka

import (
	"context"
	"log/slog"
	"time"

	"github.com/redis/go-redis/v9"
)

const fallbackListKey = "kafka:fallback:razorpay.events"

// FallbackPublish writes a message to a Redis LIST when Kafka is unavailable.
func FallbackPublish(ctx context.Context, rdb *redis.Client, payload []byte) error {
	return rdb.RPush(ctx, fallbackListKey, payload).Err()
}

// StartDrainLoop drains the Redis fallback LIST into Kafka every 10 seconds.
// Runs until ctx is cancelled (on graceful shutdown).
func StartDrainLoop(ctx context.Context, producer *Producer, rdb *redis.Client) {
	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			drainOnce(ctx, producer, rdb)
		}
	}
}

func drainOnce(ctx context.Context, producer *Producer, rdb *redis.Client) {
	count, err := rdb.LLen(ctx, fallbackListKey).Result()
	if err != nil || count == 0 {
		return
	}

	const batchSize = 100
	limit := count
	if limit > batchSize {
		limit = batchSize
	}

	for i := int64(0); i < limit; i++ {
		payload, err := rdb.LIndex(ctx, fallbackListKey, 0).Bytes()
		if err != nil {
			return
		}

		if err := producer.Publish(ctx, "", payload); err != nil {
			slog.Warn("fallback drain: kafka write failed, will retry", "err", err)
			return
		}

		rdb.LPop(ctx, fallbackListKey)
	}

	slog.Info("fallback drain: messages republished to kafka", "count", limit)
}
