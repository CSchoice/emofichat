# app/services/generic_chat.py
from __future__ import annotations

import backoff
from typing import List, Dict

from openai import (
    AsyncOpenAI,
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    BadRequestError,
)
from app.core.openai_client import client as openai_client

# ────────────────────────────────────────────────────────────── #
SYSTEM_PROMPT = "너는 친구처럼 대답하는 챗봇이야."
RETRY_ERRORS = (APITimeoutError, APIConnectionError, RateLimitError)

# ── (임시) 히스토리 저장소 ───────────────────────────────────── #
_history: dict[str, List[Dict[str, str]]] = {}          # → Redis 등으로 교체 예정
MAX_HISTORY = 10                                         # 최근 n 개 유지


async def load_history(user_id: str) -> list[dict[str, str]]:
    """최근 대화를 role 구조로 반환"""
    return _history.get(user_id, [])


async def save_history(user_id: str, user_msg: str, bot_msg: str) -> None:
    """간단한 in-memory 구현 (멀티 프로세스 환경이면 외부 스토어 필요)"""
    conv = _history.setdefault(user_id, [])
    conv.extend([
        {"role": "user", "content": user_msg},
        {"role": "assistant", "content": bot_msg},
    ])
    # 오래된 기록 잘라내기
    if len(conv) > MAX_HISTORY * 2:
        del conv[: len(conv) - MAX_HISTORY * 2]


# ── 메인 함수 ───────────────────────────────────────────────── #
@backoff.on_exception(backoff.expo, RETRY_ERRORS, max_tries=3)
async def get_generic_reply(user_id: str, msg: str) -> str:
    """
    잡담용 GPT-3.5-turbo 호출.
    네트워크/레이트리밋 오류 시 최대 3회 지수백오프 재시도.
    """
    history = await load_history(user_id)
    messages = [
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
        raise RuntimeError(f"OpenAI bad request: {e}") from e

    reply = resp.choices[0].message.content.strip()
    await save_history(user_id, msg, reply)
    return reply
