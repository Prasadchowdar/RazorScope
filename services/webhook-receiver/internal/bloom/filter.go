package bloom

import (
	"context"
	"log/slog"
	"strings"

	"github.com/redis/go-redis/v9"
)

const bloomKey = "bloom:razorpay:events"

// EnsureFilter initializes the bloom filter if it doesn't exist yet.
// Safe to call on every startup — BFReserve on an existing key returns an error we swallow.
func EnsureFilter(ctx context.Context, rdb *redis.Client) {
	err := rdb.Do(ctx, "BF.RESERVE", bloomKey, 0.001, 10_000_000).Err()
	if err != nil && !strings.Contains(err.Error(), "ERR item exists") {
		// Log but don't crash — bloom filter is best-effort dedup
		slog.Warn("bloom filter reserve failed", "err", err)
	}
}

// IsDuplicate returns true if this eventID has already been seen.
// Fail-open: returns false on Redis error so the event is allowed through.
func IsDuplicate(ctx context.Context, rdb *redis.Client, eventID string) bool {
	result, err := rdb.Do(ctx, "BF.EXISTS", bloomKey, eventID).Int()
	if err != nil {
		slog.Warn("bloom filter check failed (fail-open)", "event_id", eventID, "err", err)
		return false
	}
	return result == 1
}

// MarkSeen records the eventID in the bloom filter.
// Non-blocking from caller's perspective — errors are logged only.
func MarkSeen(ctx context.Context, rdb *redis.Client, eventID string) {
	if err := rdb.Do(ctx, "BF.ADD", bloomKey, eventID).Err(); err != nil {
		slog.Warn("bloom filter mark failed", "event_id", eventID, "err", err)
	}
}
