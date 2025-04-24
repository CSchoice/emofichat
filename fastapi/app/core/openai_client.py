# app/core/openai_client.py
from openai import AsyncOpenAI
from app.core.config import get_env

client = AsyncOpenAI(api_key=get_env("OPENAI_API_KEY"))
