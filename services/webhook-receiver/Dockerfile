FROM golang:1.24-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o webhook-receiver ./cmd/server

FROM alpine:3.20

RUN apk add --no-cache wget

COPY --from=builder /app/webhook-receiver /webhook-receiver

EXPOSE 8080

ENTRYPOINT ["/webhook-receiver"]
