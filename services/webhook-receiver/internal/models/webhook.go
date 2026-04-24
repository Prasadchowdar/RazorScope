package models

import (
	"encoding/json"
	"fmt"
)

// RazorpayWebhookPayload mirrors the top-level structure of all Razorpay webhook events.
type RazorpayWebhookPayload struct {
	Entity    string          `json:"entity"`
	AccountID string          `json:"account_id"`
	Event     string          `json:"event"`
	Contains  []string        `json:"contains"`
	CreatedAt int64           `json:"created_at"` // Unix timestamp
	Payload   WebhookPayloads `json:"payload"`
}

type WebhookPayloads struct {
	Payment      *PaymentWrapper      `json:"payment,omitempty"`
	Subscription *SubscriptionWrapper `json:"subscription,omitempty"`
	Invoice      *InvoiceWrapper      `json:"invoice,omitempty"`
}

type PaymentWrapper struct {
	Entity PaymentEntity `json:"entity"`
}

type PaymentEntity struct {
	ID            string `json:"id"`
	Entity        string `json:"entity"`
	Amount        int64  `json:"amount"` // paise
	Currency      string `json:"currency"`
	Status        string `json:"status"`
	Method        string `json:"method"` // upi | card | netbanking | nach
	VPA           string `json:"vpa"`    // for UPI
	Bank          string `json:"bank"`
	Description   string `json:"description"`
	ContactID     string `json:"contact_id"`
	CustomerID    string `json:"customer_id"`
	OrderID       string `json:"order_id"`
	InvoiceID     string `json:"invoice_id"`
	International bool   `json:"international"`
	Recurring     bool   `json:"recurring"`
	RecurringType string `json:"recurring_type"` // auto | manual
	CreatedAt     int64  `json:"created_at"`
}

type SubscriptionWrapper struct {
	Entity SubscriptionEntity `json:"entity"`
}

type SubscriptionEntity struct {
	ID             string            `json:"id"`
	Entity         string            `json:"entity"`
	PlanID         string            `json:"plan_id"`
	CustomerID     string            `json:"customer_id"`
	Status         string            `json:"status"`
	CurrentStart   int64             `json:"current_start"`
	CurrentEnd     int64             `json:"current_end"`
	EndedAt        int64             `json:"ended_at"`
	Quantity       int               `json:"quantity"`
	TotalCount     int               `json:"total_count"`
	PaidCount      int               `json:"paid_count"`
	RemainingCount int               `json:"remaining_count"`
	ChargeAt       int64             `json:"charge_at"`
	StartAt        int64             `json:"start_at"`
	EndAt          int64             `json:"end_at"`
	CreatedAt      int64             `json:"created_at"`
	Notes          Notes             `json:"notes,omitempty"` // merchant-defined metadata
}

// Notes accepts the different shapes Razorpay can emit in webhook payloads.
// In real test-mode traffic, notes may be an object, null, or even an empty array.
type Notes map[string]string

func (n *Notes) UnmarshalJSON(data []byte) error {
	if string(data) == "null" {
		*n = nil
		return nil
	}

	// Razorpay sometimes emits notes as [] for an empty value.
	var arr []any
	if err := json.Unmarshal(data, &arr); err == nil {
		*n = Notes{}
		return nil
	}

	var raw map[string]any
	if err := json.Unmarshal(data, &raw); err != nil {
		return err
	}

	out := make(Notes, len(raw))
	for k, v := range raw {
		switch typed := v.(type) {
		case nil:
			continue
		case string:
			out[k] = typed
		default:
			out[k] = fmt.Sprint(typed)
		}
	}

	*n = out
	return nil
}

type InvoiceWrapper struct {
	Entity InvoiceEntity `json:"entity"`
}

type InvoiceEntity struct {
	ID             string `json:"id"`
	Entity         string `json:"entity"`
	Type           string `json:"type"`
	Status         string `json:"status"`
	SubscriptionID string `json:"subscription_id"`
	CustomerID     string `json:"customer_id"`
	AmountPaid     int64  `json:"amount_paid"` // paise
	CreatedAt      int64  `json:"created_at"`
}

// KafkaMessage is the canonical event written to the razorpay.events Kafka topic.
// Flat structure so metric workers don't need to re-parse the raw JSON for common fields.
type KafkaMessage struct {
	EventID       string `json:"event_id"`
	MerchantID    string `json:"merchant_id"`
	EventType     string `json:"event_type"`
	SubID         string `json:"sub_id"`
	PaymentID     string `json:"payment_id"`
	CustomerID    string `json:"customer_id"`
	PlanID        string `json:"plan_id"`
	AmountPaise   int64  `json:"amount_paise"`
	Currency      string `json:"currency"`
	PaymentMethod string `json:"payment_method"`
	Country       string `json:"country"`        // from subscription notes["country"]
	Source        string `json:"source"`         // from subscription notes["source"]
	RawPayload    string `json:"raw_payload"`    // full original JSON for replay
	ReceivedAt    string `json:"received_at"`    // RFC3339
}
