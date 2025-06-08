"""
Redis 캐싱 및 세션 관리 모듈

Redis를 활용하여 대화 세션, 감정 데이터, 추천 결과 등을 캐싱합니다.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta

from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)

# 키 접두사 정의
USER_SESSION_PREFIX = "session:"
EMOTION_CACHE_PREFIX = "emotion:"
CONVERSATION_PREFIX = "conv:"
PRODUCT_CACHE_PREFIX = "product:"
RECOMMENDATION_PREFIX = "rec:"

# 캐시 만료 시간 (초)
SESSION_EXPIRE = 3600 * 24  # 24시간
EMOTION_EXPIRE = 3600 * 24 * 7  # 7일
PRODUCT_EXPIRE = 3600 * 24 * 3  # 3일
RECOMMENDATION_EXPIRE = 3600 * 24  # 24시간


class SessionManager:
    """사용자 세션 관리 클래스"""
    
    def __init__(self):
        self.redis = None
    
    async def _get_redis(self):
        if self.redis is None:
            self.redis = await get_redis()
        return self.redis
    
    async def create_session(self, user_id: str, session_data: Dict[str, Any]) -> str:
        """새 세션 생성"""
        redis = await self._get_redis()
        
        # 세션 ID 생성 (타임스탬프 + 사용자 ID)
        timestamp = int(datetime.now().timestamp())
        session_id = f"{timestamp}_{user_id}"
        
        # 세션 데이터에 생성 시간 추가
        session_data["created_at"] = timestamp
        session_data["last_active"] = timestamp
        
        # Redis에 세션 저장
        session_key = f"{USER_SESSION_PREFIX}{session_id}"
        await redis.set(session_key, session_data, ex=SESSION_EXPIRE)
        
        # 사용자별 활성 세션 목록에 추가
        user_sessions_key = f"{USER_SESSION_PREFIX}{user_id}:sessions"
        await redis.lpush(user_sessions_key, session_id)
        await redis.ltrim(user_sessions_key, 0, 9)  # 최근 10개 세션만 유지
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 데이터 조회"""
        redis = await self._get_redis()
        session_key = f"{USER_SESSION_PREFIX}{session_id}"
        
        session_data = await redis.get(session_key)
        if not session_data:
            return None
        
        # 마지막 활동 시간 업데이트
        session_data["last_active"] = int(datetime.now().timestamp())
        await redis.set(session_key, session_data, ex=SESSION_EXPIRE)
        
        return session_data
    
    async def update_session(self, session_id: str, update_data: Dict[str, Any]) -> bool:
        """세션 데이터 업데이트"""
        redis = await self._get_redis()
        session_key = f"{USER_SESSION_PREFIX}{session_id}"
        
        # 기존 세션 데이터 조회
        session_data = await redis.get(session_key)
        if not session_data:
            return False
        
        # 데이터 업데이트
        session_data.update(update_data)
        session_data["last_active"] = int(datetime.now().timestamp())
        
        # 업데이트된 데이터 저장
        await redis.set(session_key, session_data, ex=SESSION_EXPIRE)
        return True
    
    async def end_session(self, session_id: str) -> bool:
        """세션 종료"""
        redis = await self._get_redis()
        session_key = f"{USER_SESSION_PREFIX}{session_id}"
        
        # 세션 데이터 조회
        session_data = await redis.get(session_key)
        if not session_data:
            return False
        
        # 세션 데이터에 종료 시간 추가
        session_data["ended_at"] = int(datetime.now().timestamp())
        
        # 업데이트된 데이터 저장 (만료 시간 설정)
        await redis.set(session_key, session_data, ex=SESSION_EXPIRE)
        return True
    
    async def get_user_sessions(self, user_id: str, limit: int = 5) -> List[str]:
        """사용자의 최근 세션 목록 조회"""
        redis = await self._get_redis()
        user_sessions_key = f"{USER_SESSION_PREFIX}{user_id}:sessions"
        
        # 최근 세션 ID 목록 조회
        session_ids = await redis.lrange(user_sessions_key, 0, limit - 1)
        return session_ids


class EmotionCache:
    """감정 데이터 캐싱 클래스"""
    
    def __init__(self):
        self.redis = None
    
    async def _get_redis(self):
        if self.redis is None:
            self.redis = await get_redis()
        return self.redis
    
    async def cache_emotion(self, user_id: str, emotion_data: Dict[str, Any]) -> bool:
        """감정 분석 결과 캐싱"""
        redis = await self._get_redis()
        
        # 타임스탬프 추가
        timestamp = int(datetime.now().timestamp())
        emotion_data["timestamp"] = timestamp
        
        # 최근 감정 데이터 캐싱
        latest_key = f"{EMOTION_CACHE_PREFIX}{user_id}:latest"
        await redis.set(latest_key, emotion_data, ex=EMOTION_EXPIRE)
        
        # 감정 이력에 추가
        history_key = f"{EMOTION_CACHE_PREFIX}{user_id}:history"
        await redis.lpush(history_key, emotion_data)
        await redis.ltrim(history_key, 0, 99)  # 최근 100개 기록만 유지
        
        return True
    
    async def get_latest_emotion(self, user_id: str) -> Optional[Dict[str, Any]]:
        """최근 감정 데이터 조회"""
        redis = await self._get_redis()
        latest_key = f"{EMOTION_CACHE_PREFIX}{user_id}:latest"
        
        return await redis.get(latest_key)
    
    async def get_emotion_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """감정 이력 조회"""
        redis = await self._get_redis()
        history_key = f"{EMOTION_CACHE_PREFIX}{user_id}:history"
        
        return await redis.lrange(history_key, 0, limit - 1)
    
    async def get_emotion_trend(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """감정 트렌드 분석 결과 조회"""
        redis = await self._get_redis()
        history_key = f"{EMOTION_CACHE_PREFIX}{user_id}:history"
        
        # 감정 이력 조회
        emotion_history = await redis.lrange(history_key, 0, 99)
        
        # 현재 시간 기준으로 특정 일수 이내의 데이터만 필터링
        cutoff_time = int((datetime.now() - timedelta(days=days)).timestamp())
        recent_emotions = [
            e for e in emotion_history 
            if e.get("timestamp", 0) >= cutoff_time
        ]
        
        if not recent_emotions:
            return {
                "user_id": user_id,
                "days": days,
                "data_points": 0,
                "message": "감정 데이터가 충분하지 않습니다."
            }
        
        # 감정 빈도 계산
        emotion_frequency = {}
        for e in recent_emotions:
            emotion = e.get("dominant_emotion", "중립")
            emotion_frequency[emotion] = emotion_frequency.get(emotion, 0) + 1
        
        # 가장 빈번한 감정 찾기
        most_frequent = max(emotion_frequency.items(), key=lambda x: x[1])
        
        # 부정/불안 비율 계산
        negative_count = sum(1 for e in recent_emotions if e.get("is_negative", False))
        anxious_count = sum(1 for e in recent_emotions if e.get("is_anxious", False))
        
        # 감정 변동성 계산 (연속된 감정 변화 횟수)
        volatility = 0
        prev_emotion = None
        for e in recent_emotions:
            curr_emotion = e.get("dominant_emotion")
            if prev_emotion and curr_emotion != prev_emotion:
                volatility += 1
            prev_emotion = curr_emotion
        
        # 정규화된 변동성 (0~1 사이)
        norm_volatility = volatility / (len(recent_emotions) - 1) if len(recent_emotions) > 1 else 0
        
        return {
            "user_id": user_id,
            "days": days,
            "data_points": len(recent_emotions),
            "most_frequent_emotion": most_frequent[0],
            "emotion_frequency": emotion_frequency,
            "negative_ratio": negative_count / len(recent_emotions),
            "anxious_ratio": anxious_count / len(recent_emotions),
            "emotion_volatility": norm_volatility
        }


class ProductCache:
    """금융 상품 캐싱 클래스"""
    
    def __init__(self):
        self.redis = None
    
    async def _get_redis(self):
        if self.redis is None:
            self.redis = await get_redis()
        return self.redis
    
    async def cache_product(self, product_id: str, product_data: Dict[str, Any]) -> bool:
        """상품 정보 캐싱"""
        redis = await self._get_redis()
        product_key = f"{PRODUCT_CACHE_PREFIX}{product_id}"
        
        await redis.set(product_key, product_data, ex=PRODUCT_EXPIRE)
        
        # 상품 유형별 목록에 추가
        product_type = product_data.get("type", "unknown")
        type_key = f"{PRODUCT_CACHE_PREFIX}type:{product_type}"
        await redis.lpush(type_key, product_id)
        
        return True
    
    async def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """상품 정보 조회"""
        redis = await self._get_redis()
        product_key = f"{PRODUCT_CACHE_PREFIX}{product_id}"
        
        return await redis.get(product_key)
    
    async def get_products_by_type(self, product_type: str, limit: int = 10) -> List[str]:
        """상품 유형별 ID 목록 조회"""
        redis = await self._get_redis()
        type_key = f"{PRODUCT_CACHE_PREFIX}type:{product_type}"
        
        return await redis.lrange(type_key, 0, limit - 1)
    
    async def cache_recommendation(self, user_id: str, product_type: str, recommendations: List[Dict[str, Any]]) -> bool:
        """추천 결과 캐싱"""
        redis = await self._get_redis()
        
        # 타임스탬프 추가
        timestamp = int(datetime.now().timestamp())
        rec_data = {
            "timestamp": timestamp,
            "product_type": product_type,
            "recommendations": recommendations
        }
        
        # 추천 결과 캐싱
        rec_key = f"{RECOMMENDATION_PREFIX}{user_id}:{product_type}"
        await redis.set(rec_key, rec_data, ex=RECOMMENDATION_EXPIRE)
        
        return True
    
    async def get_recommendation(self, user_id: str, product_type: str) -> Optional[Dict[str, Any]]:
        """추천 결과 조회"""
        redis = await self._get_redis()
        rec_key = f"{RECOMMENDATION_PREFIX}{user_id}:{product_type}"
        
        return await redis.get(rec_key)


# 싱글톤 인스턴스
_session_manager = None
_emotion_cache = None
_product_cache = None


def get_session_manager() -> SessionManager:
    """세션 관리자 싱글톤 인스턴스 반환"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def get_emotion_cache() -> EmotionCache:
    """감정 캐시 싱글톤 인스턴스 반환"""
    global _emotion_cache
    if _emotion_cache is None:
        _emotion_cache = EmotionCache()
    return _emotion_cache


def get_product_cache() -> ProductCache:
    """상품 캐시 싱글톤 인스턴스 반환"""
    global _product_cache
    if _product_cache is None:
        _product_cache = ProductCache()
    return _product_cache
