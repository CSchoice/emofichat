import os
import logging
import json
from typing import Any
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

class MemoryCache:
    """Redis 대체용 메모리 캐시"""
    def __init__(self):
        self.data: dict[str, Any] = {}

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> Any:
        value = self.data.get(key)
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    async def set(self, key: str, value: Any, ex: int | None = None) -> bool:
        if isinstance(value, (list, dict)):
            self.data[key] = json.dumps(value)
        else:
            self.data[key] = value
        return True

    async def delete(self, key: str) -> int:
        if key in self.data:
            del self.data[key]
            return 1
        return 0

    async def lrange(self, key: str, start: int, end: int) -> list:
        seq = self.data.get(key, [])
        if not isinstance(seq, list):
            return []
        return seq[start:end+1] if end != -1 else seq[start:]

    async def lpush(self, key: str, *values: Any) -> int:
        seq = self.data.setdefault(key, [])
        if not isinstance(seq, list):
            seq = []
            self.data[key] = seq
        for v in values:
            seq.insert(0, v)
        return len(seq)

    async def rpush(self, key: str, *values: Any) -> int:
        seq = self.data.setdefault(key, [])
        if not isinstance(seq, list):
            seq = []
            self.data[key] = seq
        seq.extend(values)
        return len(seq)

    async def ltrim(self, key: str, start: int, end: int) -> bool:
        seq = self.data.get(key, [])
        if not isinstance(seq, list):
            return False
        self.data[key] = seq[start:end+1] if end != -1 else seq[start:]
        return True

# 전역 memory cache
memory_cache = MemoryCache()

# Redis 싱글톤 및 접속 시도 플래그
_redis_client: Redis | None = None
_redis_tried: bool = False

class CacheProxy:
    """Redis 또는 MemoryCache를 감싸서 자동 직렬화/역직렬화 및 WRONGTYPE 방지"""
    def __init__(self, client: Any):
        self._client = client

    async def ping(self) -> bool:
        return await self._client.ping()

    async def get(self, key: str) -> Any:
        return await self._client.get(key)

    async def set(self, key: str, value: Any, ex: int | None = None) -> bool:
        if isinstance(self._client, Redis):
            await self._client.delete(key)
            if isinstance(value, list):
                await self._client.rpush(key, *value)
                if ex:
                    await self._client.expire(key, ex)
                return True
            if isinstance(value, dict):
                value = json.dumps(value)
            return await self._client.set(key, value, ex)
        return await self._client.set(key, value, ex)

    async def delete(self, key: str) -> Any:
        if isinstance(self._client, Redis):
            return await self._client.delete(key)
        return await self._client.delete(key)

    async def lpush(self, key: str, *values: Any) -> int:
        return await self._client.lpush(key, *values)

    async def rpush(self, key: str, *values: Any) -> int:
        return await self._client.rpush(key, *values)

    async def lrange(self, key: str, start: int, end: int) -> list:
        return await self._client.lrange(key, start, end)

    async def ltrim(self, key: str, start: int, end: int) -> bool:
        return await self._client.ltrim(key, start, end)

    def pipeline(self) -> "PipelineProxy":
        return PipelineProxy(self)

class PipelineProxy:
    """Redis 또는 MemoryCache 파이프라인 래퍼 — WRONGTYPE 방지"""
    def __init__(self, client: Any):
        self.client = client
        self.commands: list[tuple[str, str, tuple[Any, ...]]] = []

    def lpush(self, key: str, *values: Any):
        self.commands.append(("lpush", key, values))
        return self

    def rpush(self, key: str, *values: Any):
        self.commands.append(("rpush", key, values))
        return self

    def ltrim(self, key: str, start: int, end: int):
        self.commands.append(("ltrim", key, (start, end)))
        return self

    async def execute(self) -> list[Any]:
        results: list[Any] = []
        for op, key, args in self.commands:
            if op == "lpush":
                res = await self.client.lpush(key, *args)
            elif op == "rpush":
                res = await self.client.rpush(key, *args)
            elif op == "ltrim":
                start, end = args  # type: ignore
                res = await self.client.ltrim(key, start, end)
            else:
                continue
            results.append(res)
        self.commands.clear()
        return results

async def get_redis() -> CacheProxy:
    """
    - 최초 호출 시 REDIS_URL로 접속 시도
    - 접속 성공하면 Redis Proxy 객체 반환
    - 접속 실패하면 MemoryCache Proxy 반환
    - 이후 호출은 동일한 Proxy 객체 반환
    """
    global _redis_client, _redis_tried

    if not _redis_tried:
        _redis_tried = True
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        logger.debug(f"Connecting to Redis at {redis_url}")
        try:
            client = Redis.from_url(redis_url, decode_responses=True)
            await client.ping()
            _redis_client = client
            logger.info("Successfully connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis ({redis_url}): {e}")

    if _redis_client is not None:
        return CacheProxy(_redis_client)
    logger.warning("Using in-memory cache instead of Redis")
    return CacheProxy(memory_cache)
