from redis.asyncio import Redis
import os
import logging

_redis_client = None
_redis_available = False  # Redis 사용 가능 여부 플래그

logger = logging.getLogger(__name__)

async def get_redis() -> Redis:
    """
    레디스 클라이언트 싱글톤 반환
    환경변수: REDIS_URL
    
    Redis 연결 불가시 메모리 폴백을 위해 None 반환
    """
    global _redis_client, _redis_available
    
    # 이미 Redis 사용 불가로 판단됐으면 바로 None 반환
    if not _redis_available and _redis_client is None:
        logger.warning("Redis is not available, using in-memory fallback")
        return None
    
    if _redis_client is None:
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            logger.debug(f"Connecting to Redis at {redis_url}")
            
            _redis_client = Redis.from_url(redis_url, decode_responses=True)
            # 연결 테스트
            await _redis_client.ping()
            logger.info("Successfully connected to Redis")
            _redis_available = True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            _redis_available = False
            return None
        
    return _redis_client

# 메모리 기반 대체 구현 (Redis 연결 실패시 사용)
class MemoryCache:
    """Redis 대신 사용할 메모리 기반 캐시"""
    def __init__(self):
        self.data = {}
        
    async def ping(self):
        return True
    
    async def get(self, key):
        return self.data.get(key)
    
    async def set(self, key, value, ex=None):
        self.data[key] = value
        return True
    
    async def lrange(self, key, start, end):
        return self.data.get(key, [])[start:end if end != -1 else None]
    
    async def lpush(self, key, *values):
        if key not in self.data:
            self.data[key] = []
        self.data[key] = list(values) + self.data[key]
        return len(self.data[key])
    
    async def rpush(self, key, *values):
        if key not in self.data:
            self.data[key] = []
        self.data[key].extend(values)
        return len(self.data[key])
    
    async def ltrim(self, key, start, end):
        if key in self.data:
            self.data[key] = self.data[key][start:end if end != -1 else None]
        return True
    
    def pipeline(self):
        return MemoryPipeline(self)

class MemoryPipeline:
    """메모리 캐시용 파이프라인"""
    def __init__(self, cache):
        self.cache = cache
        self.commands = []
        
    def lpush(self, key, *values):
        self.commands.append(("lpush", key, values))
        return self
    
    def rpush(self, key, *values):
        self.commands.append(("rpush", key, values))
        return self
    
    def ltrim(self, key, start, end):
        self.commands.append(("ltrim", key, start, end))
        return self
    
    async def execute(self):
        results = []
        for cmd in self.commands:
            if cmd[0] == "lpush":
                results.append(await self.cache.lpush(cmd[1], *cmd[2]))
            elif cmd[0] == "rpush":
                results.append(await self.cache.rpush(cmd[1], *cmd[2]))
            elif cmd[0] == "ltrim":
                results.append(await self.cache.ltrim(cmd[1], cmd[2], cmd[3]))
        self.commands = []
        return results

# 전역 메모리 캐시 인스턴스
memory_cache = MemoryCache()
