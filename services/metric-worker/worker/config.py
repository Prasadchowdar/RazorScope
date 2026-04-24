import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    KAFKA_BROKERS: list[str] = os.getenv("KAFKA_BROKERS", "localhost:29092").split(",")
    KAFKA_TOPIC: str = os.getenv("KAFKA_TOPIC", "razorpay.events")
    KAFKA_GROUP_ID: str = os.getenv("KAFKA_GROUP_ID", "razorscope-metric-workers")

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://razorscope:razorscope_dev@localhost:5432/razorscope",
    )

    CLICKHOUSE_HOST: str = os.getenv("CLICKHOUSE_HOST", "localhost")
    CLICKHOUSE_PORT: int = int(os.getenv("CLICKHOUSE_PORT", "8123"))
    CLICKHOUSE_USER: str = os.getenv("CLICKHOUSE_USER", "razorscope")
    CLICKHOUSE_PASSWORD: str = os.getenv("CLICKHOUSE_PASSWORD", "razorscope_dev")
    CLICKHOUSE_DB: str = os.getenv("CLICKHOUSE_DB", "razorscope")

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    RAZORPAY_SECRET_ENCRYPTION_KEY: str = os.getenv(
        "RAZORPAY_SECRET_ENCRYPTION_KEY",
        "razorscope-dev-razorpay-secret",
    )

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
