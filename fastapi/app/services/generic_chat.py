from __future__ import annotations

import json, backoff
from typing import List, Dict, Any

from openai import (
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    BadRequestError,
)
from openai import AsyncOpenAI
from app.core.openai_client import client as openai_client
from app.core.redis_client import get_redis                     # ⭐ Redis 클라이언트
# ---------------------------------------------------------------- #
SYSTEM_PROMPT = "너는 친구처럼 대답하는 챗봇이야."
RETRY_ERRORS = (APITimeoutError, APIConnectionError, RateLimitError)
MAX_HISTORY = 10          # user/assistant 쌍의 최대 보존 개수
# ---------------------------------------------------------------- #

# ─────────────────────── 히스토리 I/O ──────────────────────────── #
async def load_history(user_id: str) -> List[Dict[str, str]]:
    """
    Redis 리스트 → List[{role, content}]  
    키: hist:{user_id}
    """
    r = await get_redis()
    raw_items = await r.lrange(f"hist:{user_id}", 0, -1)
    return [json.loads(x) for x in raw_items] if raw_items else []


async def save_history(user_id: str, user_msg: str, bot_msg: str) -> None:
    """
    user/assistant 쌍 2개 push 후 길이 제한
    """
    r = await get_redis()
    pipe = r.pipeline()
    pipe.rpush(
        f"hist:{user_id}",
        json.dumps({"role": "user", "content": user_msg}, ensure_ascii=False),
        json.dumps({"role": "assistant", "content": bot_msg}, ensure_ascii=False),
    )
    pipe.ltrim(f"hist:{user_id}", -MAX_HISTORY * 2, -1)
    await pipe.execute()

# ─────────────────────── GPT-3.5 호출 함수 ────────────────────── #
@backoff.on_exception(backoff.expo, RETRY_ERRORS, max_tries=3)
async def get_generic_reply(user_id: str, msg: str) -> str:
    """
    1️⃣ Redis 에서 최근 대화 히스토리 로드  
    2️⃣ GPT-3.5-turbo-0125 호출(temperature 0.8)  
    3️⃣ 답변 저장 → Redis
    """
    history = await load_history(user_id)

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": msg},
    ]

    try:
        resp = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            temperature=0.8,
            max_tokens=150,
            messages=messages,
        )
    except BadRequestError as e:
        # 프롬프트 오류는 치명적이므로 에러 전파
        raise RuntimeError(f"OpenAI bad request: {e}") from e

    reply: str = resp.choices[0].message.content.strip()
    await save_history(user_id, msg, reply)
    return reply
