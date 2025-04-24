from __future__ import annotations

import json, backoff
from typing import List, Dict, Any
import logging

from openai import (
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    BadRequestError,
)
from openai import AsyncOpenAI
from app.core.openai_client import client as openai_client
from app.core.redis_client import get_redis, memory_cache  # Redis 클라이언트 + 메모리 캐시
# ---------------------------------------------------------------- #
SYSTEM_PROMPT = "너는 친구처럼 대답하는 챗봇이야."
RETRY_ERRORS = (APITimeoutError, APIConnectionError, RateLimitError)
MAX_HISTORY = 10          # user/assistant 쌍의 최대 보존 개수
# ---------------------------------------------------------------- #

# 로깅 추가
logger = logging.getLogger(__name__)

# ─────────────────────── 히스토리 I/O ──────────────────────────── #

async def load_history(user_id: str) -> List[Dict[str, str]]:
    """
    히스토리 가져오기 - Redis 연결 실패시 메모리 캐시 사용
    """
    logger.debug(f"Loading history for user {user_id}")
    
    # Redis 커넥션 열기
    r = await get_redis()
    
    # Redis 연결 실패시 메모리 캐시 사용
    if r is None:
        history_data = memory_cache.data.get(f"hist:{user_id}", [])
        # 문자열로 저장되어 있는 경우 파싱
        result = []
        for item in history_data:
            if isinstance(item, str):
                try:
                    result.append(json.loads(item))
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse history item: {item}")
            else:
                result.append(item)
        return result
    
    # Redis 연결 성공시
    try:
        raw_items = await r.lrange(f"hist:{user_id}", 0, -1)
        # 문자열로 저장되어 있는 경우 파싱
        result = []
        for item in raw_items:
            if isinstance(item, str):
                try:
                    result.append(json.loads(item))
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse history item: {item}")
            else:
                result.append(item)
        return result
    except Exception as e:
        logger.error(f"Error loading history from Redis: {str(e)}")
        return []  # 에러시 메모리 캐시 사용


async def save_history(user_id: str, user_msg: str, bot_msg: str) -> None:
    """
    user/assistant 쌍 2개 push 후 길이 제한
    """
    user_data = {"role": "user", "content": user_msg}
    bot_data = {"role": "assistant", "content": bot_msg}
    
    # Redis 커넥션 열기
    r = await get_redis()
    
    # Redis 연결 실패시 메모리 캐시 사용
    if r is None:
        key = f"hist:{user_id}"
        if key not in memory_cache.data:
            memory_cache.data[key] = []
        
        # 객체 자체를 저장 (문자열로 저장하지 않음)
        memory_cache.data[key].append(user_data)
        memory_cache.data[key].append(bot_data)
        
        # 길이 제한
        if len(memory_cache.data[key]) > MAX_HISTORY * 2:
            memory_cache.data[key] = memory_cache.data[key][-MAX_HISTORY * 2:]
            
        logger.debug(f"Saved history to memory cache for {user_id}, items: {len(memory_cache.data[key])}")
        return
    
    # Redis 연결 성공시
    try:
        pipe = r.pipeline()
        # 직렬화된 문자열로 저장 - Redis는 문자열만 저장 가능
        pipe.rpush(
            f"hist:{user_id}",
            json.dumps(user_data, ensure_ascii=False),
            json.dumps(bot_data, ensure_ascii=False),
        )
        pipe.ltrim(f"hist:{user_id}", -MAX_HISTORY * 2, -1)
        await pipe.execute()
        logger.debug(f"Saved history to Redis for {user_id}")
    except Exception as e:
        logger.error(f"Error saving history to Redis: {str(e)}")
        
        # 에러시 메모리 캐시로 폴백
        key = f"hist:{user_id}"
        if key not in memory_cache.data:
            memory_cache.data[key] = []
            
        memory_cache.data[key].append(user_data)
        memory_cache.data[key].append(bot_data)

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
