from fastapi import Request
from slowapi import Limiter


def _rate_key(request: Request) -> str:
    return getattr(request.state, "merchant_id", request.client.host)


limiter = Limiter(key_func=_rate_key)
