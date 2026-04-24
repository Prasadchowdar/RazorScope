from openai import OpenAI
from api.config import Config

def get_client() -> OpenAI:
    if not Config.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=Config.OPENAI_API_KEY)
