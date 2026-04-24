import os
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()


class Config:
    APP_ENV: str = os.getenv("APP_ENV", "development").lower()
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://razorscope_app:app_dev_password@localhost:5432/razorscope",
    )
    CLICKHOUSE_HOST: str = os.getenv("CLICKHOUSE_HOST", "localhost")
    CLICKHOUSE_PORT: int = int(os.getenv("CLICKHOUSE_PORT", "8123"))
    CLICKHOUSE_USER: str = os.getenv("CLICKHOUSE_USER", "razorscope")
    CLICKHOUSE_PASSWORD: str = os.getenv("CLICKHOUSE_PASSWORD", "razorscope_dev")
    CLICKHOUSE_DB: str = os.getenv("CLICKHOUSE_DB", "razorscope")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    PORT: int = int(os.getenv("PORT", "8000"))
    WEBHOOK_BASE_URL: str = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8080")
    RAZORPAY_SECRET_ENCRYPTION_KEY: str = os.getenv(
        "RAZORPAY_SECRET_ENCRYPTION_KEY",
        "razorscope-dev-razorpay-secret",
    )
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_32bytes+")
    JWT_ACCESS_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_EXPIRE_MINUTES", "15"))
    JWT_REFRESH_EXPIRE_DAYS: int = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", "7"))
    REFRESH_COOKIE_NAME: str = "rzs_refresh"
    REFRESH_COOKIE_SECURE: bool = os.getenv("REFRESH_COOKIE_SECURE", "false").lower() == "true"
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3001"
    ).split(",")

    @classmethod
    def validate_runtime(cls) -> None:
        if cls.APP_ENV != "production":
            return

        errors: list[str] = []
        if cls.JWT_SECRET_KEY == "CHANGE_ME_IN_PRODUCTION_32bytes+" or len(cls.JWT_SECRET_KEY) < 32:
            errors.append("JWT_SECRET_KEY must be a strong production secret")
        if (
            cls.RAZORPAY_SECRET_ENCRYPTION_KEY == "razorscope-dev-razorpay-secret"
            or len(cls.RAZORPAY_SECRET_ENCRYPTION_KEY) < 32
        ):
            errors.append("RAZORPAY_SECRET_ENCRYPTION_KEY must be a strong production secret")
        if not cls.REFRESH_COOKIE_SECURE:
            errors.append("REFRESH_COOKIE_SECURE must be true in production")

        webhook = urlparse(cls.WEBHOOK_BASE_URL)
        if webhook.scheme != "https" or webhook.hostname in {"localhost", "127.0.0.1"}:
            errors.append("WEBHOOK_BASE_URL must be a public https URL in production")

        invalid_origins = [
            origin for origin in cls.CORS_ORIGINS
            if not origin
            or not origin.startswith("https://")
            or "localhost" in origin
            or "127.0.0.1" in origin
        ]
        if invalid_origins:
            errors.append("CORS_ORIGINS must only contain public https origins in production")

        if errors:
            raise RuntimeError("Invalid production configuration: " + "; ".join(errors))
