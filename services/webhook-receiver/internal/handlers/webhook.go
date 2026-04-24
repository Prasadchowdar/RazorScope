package handlers

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log/slog"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"

	"github.com/razorscope/webhook-receiver/internal/bloom"
	"github.com/razorscope/webhook-receiver/internal/db"
	kafkapkg "github.com/razorscope/webhook-receiver/internal/kafka"
	"github.com/razorscope/webhook-receiver/internal/models"
)

type WebhookHandler struct {
	pool                  *pgxpool.Pool
	rdb                   *redis.Client
	producer              *kafkapkg.Producer
	timestampToleranceSec int64
}

func NewWebhookHandler(
	pool *pgxpool.Pool,
	rdb *redis.Client,
	producer *kafkapkg.Producer,
	timestampToleranceSec int64,
) *WebhookHandler {
	return &WebhookHandler{
		pool:                  pool,
		rdb:                   rdb,
		producer:              producer,
		timestampToleranceSec: timestampToleranceSec,
	}
}

func (h *WebhookHandler) Handle(c *fiber.Ctx) error {
	merchantID := c.Params("merchantID")
	if merchantID == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "missing merchant id"})
	}

	// Step 1 — capture raw body BEFORE any parsing
	rawBody := c.Body()

	// Step 2 — HMAC-SHA256 signature verification
	sigHeader := c.Get("X-Razorpay-Signature")
	if sigHeader == "" {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"error": "missing signature"})
	}

	ctx := c.Context()
	secret, err := db.GetMerchantWebhookSecret(ctx, h.pool, merchantID)
	if err != nil || secret == "" {
		slog.Warn("merchant not found or no secret", "merchant_id", merchantID, "err", err)
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"error": "invalid merchant"})
	}

	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write(rawBody)
	computed := hex.EncodeToString(mac.Sum(nil))

	// constant-time comparison prevents timing attacks
	if !hmac.Equal([]byte(computed), []byte(sigHeader)) {
		slog.Warn("signature mismatch", "merchant_id", merchantID)
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"error": "invalid signature"})
	}

	// Step 3 — parse payload and check timestamp
	var payload models.RazorpayWebhookPayload
	if err := json.Unmarshal(rawBody, &payload); err != nil {
		slog.Warn("invalid webhook json", "merchant_id", merchantID, "err", err)
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid json"})
	}

	age := time.Now().Unix() - payload.CreatedAt
	if age > h.timestampToleranceSec || age < -60 {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": fmt.Sprintf("event timestamp out of tolerance window (%ds)", age),
		})
	}

	// Step 4 — extract event_id and entity fields
	eventID, paymentID, subID, customerID, planID, amountPaise, currency, paymentMethod, country, source := extractEntityFields(payload)

	// Step 5 — bloom filter deduplication (fail-open)
	if bloom.IsDuplicate(ctx, h.rdb, eventID) {
		slog.Info("duplicate event", "event_id", eventID, "merchant_id", merchantID)
		return c.Status(fiber.StatusOK).JSON(fiber.Map{"status": "duplicate", "event_id": eventID})
	}

	// Step 6 — build canonical Kafka message
	msg := models.KafkaMessage{
		EventID:       eventID,
		MerchantID:    merchantID,
		EventType:     payload.Event,
		SubID:         subID,
		PaymentID:     paymentID,
		CustomerID:    customerID,
		PlanID:        planID,
		AmountPaise:   amountPaise,
		Currency:      currency,
		PaymentMethod: paymentMethod,
		Country:       country,
		Source:        source,
		RawPayload:    string(rawBody),
		ReceivedAt:    time.Now().UTC().Format(time.RFC3339),
	}

	msgBytes, err := json.Marshal(msg)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "serialization error"})
	}

	// Step 7 — synchronous Kafka write with fallback
	writeCtx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	var kafkaOffset *int64
	kafkaErr := h.producer.Publish(writeCtx, merchantID, msgBytes)
	if kafkaErr != nil {
		slog.Warn("kafka write failed, using redis fallback", "event_id", eventID, "err", kafkaErr)
		if fbErr := kafkapkg.FallbackPublish(writeCtx, h.rdb, msgBytes); fbErr != nil {
			slog.Error("both kafka and fallback failed", "event_id", eventID, "err", fbErr)
		}
	}

	// Step 8 — mark bloom filter (non-blocking, after successful path)
	go bloom.MarkSeen(context.Background(), h.rdb, eventID)

	// Step 9 — record delivery (async, non-blocking)
	deliveryStatus := "received"
	errDetail := ""
	if kafkaErr != nil {
		deliveryStatus = "fallback"
		errDetail = kafkaErr.Error()
	}
	go db.RecordWebhookDelivery(context.Background(), h.pool, merchantID, eventID, payload.Event, deliveryStatus, kafkaOffset, errDetail)

	return c.Status(fiber.StatusOK).JSON(fiber.Map{"status": "accepted", "event_id": eventID})
}

func extractEntityFields(p models.RazorpayWebhookPayload) (
	eventID, paymentID, subID, customerID, planID string,
	amountPaise int64, currency, paymentMethod, country, source string,
) {
	currency = "INR"
	paymentMethod = "unknown"

	if p.Payload.Payment != nil {
		pay := p.Payload.Payment.Entity
		paymentID = pay.ID
		eventID = pay.ID
		amountPaise = pay.Amount
		currency = pay.Currency
		customerID = pay.CustomerID
		paymentMethod = normalizeMethod(pay.Method, pay.VPA)
	}

	if p.Payload.Subscription != nil {
		sub := p.Payload.Subscription.Entity
		subID = sub.ID
		customerID = sub.CustomerID
		planID = sub.PlanID
		if eventID == "" {
			eventID = sub.ID
		}
		if sub.Notes != nil {
			country = sub.Notes["country"]
			source = sub.Notes["source"]
		}
	}

	if p.Payload.Invoice != nil {
		inv := p.Payload.Invoice.Entity
		if subID == "" {
			subID = inv.SubscriptionID
		}
		if eventID == "" {
			eventID = inv.ID
		}
	}

	// Deterministic fallback when no entity ID is present
	if eventID == "" {
		h := sha256.New()
		h.Write([]byte(p.Event + p.AccountID + fmt.Sprint(p.CreatedAt)))
		eventID = "synth_" + hex.EncodeToString(h.Sum(nil))[:16]
	}

	return
}

func normalizeMethod(method, vpa string) string {
	switch method {
	case "upi":
		if vpa != "" {
			return "upi_autopay"
		}
		return "upi_collect"
	case "card":
		return "card"
	case "nach":
		return "nach"
	case "netbanking":
		return "netbanking"
	default:
		return method
	}
}
