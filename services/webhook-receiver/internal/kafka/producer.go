package kafka

import (
	"context"
	"fmt"
	"time"

	"github.com/segmentio/kafka-go"
)

type Producer struct {
	writer *kafka.Writer
	topic  string
}

func NewProducer(brokers []string, topic string, writeTimeout time.Duration) *Producer {
	w := &kafka.Writer{
		Addr:         kafka.TCP(brokers...),
		Topic:        topic,
		Balancer:     &kafka.Hash{},     // consistent partition by key (merchantID)
		RequiredAcks: kafka.RequireOne,  // leader ack — acceptable for webhook ingestion
		WriteTimeout: writeTimeout,
		Async:        false,             // synchronous — we must know if write succeeded
		BatchSize:    1,                 // no batching on hot path
	}
	return &Producer{writer: w, topic: topic}
}

// Publish writes a message to Kafka with merchantID as the partition key.
func (p *Producer) Publish(ctx context.Context, merchantID string, payload []byte) error {
	err := p.writer.WriteMessages(ctx, kafka.Message{
		Key:   []byte(merchantID),
		Value: payload,
	})
	if err != nil {
		return fmt.Errorf("kafka write: %w", err)
	}
	return nil
}

func (p *Producer) Close() error {
	return p.writer.Close()
}
