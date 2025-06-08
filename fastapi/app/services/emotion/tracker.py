"""
감정 추적기

사용자의 감정 변화를 추적하고 기록합니다.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# 로거 설정
logger = logging.getLogger(__name__)

class EmotionTracker:
    """감정 추적 클래스"""
    
    def __init__(self, db_client=None):
        self.db = db_client
        
    async def record_emotion(self, user_id: str, emotion_data: Dict[str, Any]) -> bool:
        """
        사용자의 감정 데이터를 기록
        
        Args:
            user_id: 사용자 ID
            emotion_data: 감정 분석 결과
            
        Returns:
            기록 성공 여부
        """
        try:
            # 기록할 데이터 구성
            record = {
                "user_id": user_id,
                "timestamp": datetime.now(),
                "dominant_emotion": emotion_data.get("dominant_emotion", "중립"),
                "dominant_score": emotion_data.get("dominant_score", 0.0),
                "is_negative": emotion_data.get("is_negative", False),
                "is_anxious": emotion_data.get("is_anxious", False),
                "all_emotions": emotion_data.get("all_emotions", {})
            }
            
            # DB 연결이 있는 경우 DB에 저장
            if self.db:
                await self.db.emotion_history.insert_one(record)
                logger.debug(f"감정 데이터 DB 저장 완료: {user_id}")
            else:
                # DB 연결이 없는 경우 로그만 남김
                logger.info(f"감정 데이터 기록 (DB 없음): {user_id}, {record['dominant_emotion']}")
                
            return True
            
        except Exception as e:
            logger.error(f"감정 데이터 기록 실패: {str(e)}")
            return False
            
    async def get_emotion_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        사용자의 감정 기록 조회
        
        Args:
            user_id: 사용자 ID
            limit: 조회할 최대 기록 수
            
        Returns:
            감정 기록 목록
        """
        try:
            # DB 연결이 있는 경우 DB에서 조회
            if self.db:
                cursor = self.db.emotion_history.find(
                    {"user_id": user_id},
                    sort=[("timestamp", -1)],
                    limit=limit
                )
                return await cursor.to_list(length=limit)
            else:
                # DB 연결이 없는 경우 빈 목록 반환
                logger.info(f"감정 기록 조회 (DB 없음): {user_id}")
                return []
                
        except Exception as e:
            logger.error(f"감정 기록 조회 실패: {str(e)}")
            return []
            
    async def analyze_emotion_trend(self, user_id: str, window: int = 5) -> Dict[str, Any]:
        """
        사용자의 감정 변화 추세 분석
        
        Args:
            user_id: 사용자 ID
            window: 분석할 기록 수
            
        Returns:
            감정 추세 분석 결과
        """
        # 감정 기록 조회
        history = await self.get_emotion_history(user_id, limit=window)
        
        # 기록이 없는 경우
        if not history:
            return {
                "trend": "unknown",
                "dominant_emotion": "중립",
                "is_stable": True,
                "is_improving": False,
                "negative_ratio": 0.0,
                "anxiety_ratio": 0.0
            }
            
        # 감정 변화 분석
        emotions = [record.get("dominant_emotion") for record in history]
        scores = [record.get("dominant_score", 0.0) for record in history]
        is_negatives = [record.get("is_negative", False) for record in history]
        is_anxious = [record.get("is_anxious", False) for record in history]
        
        # 최근 주요 감정
        recent_emotion = emotions[0] if emotions else "중립"
        
        # 감정 안정성 (동일한 감정의 비율)
        if emotions:
            most_common = max(set(emotions), key=emotions.count)
            stability = emotions.count(most_common) / len(emotions)
        else:
            stability = 1.0
            most_common = "중립"
        
        # 부정적 감정 비율
        negative_ratio = sum(is_negatives) / len(is_negatives) if is_negatives else 0.0
        
        # 불안 감정 비율
        anxiety_ratio = sum(is_anxious) / len(is_anxious) if is_anxious else 0.0
        
        # 감정 개선 여부 (부정->긍정 변화)
        is_improving = False
        if len(is_negatives) >= 2:
            # 과거에는 부정적이었으나 최근에는 긍정적인 경우
            if sum(is_negatives[1:]) > 0 and not is_negatives[0]:
                is_improving = True
        
        # 감정 추세 결정
        if stability >= 0.7:
            trend = "stable"  # 안정적
        elif negative_ratio >= 0.7:
            trend = "negative"  # 부정적
        elif negative_ratio <= 0.3:
            trend = "positive"  # 긍정적
        elif anxiety_ratio >= 0.5:
            trend = "anxious"  # 불안
        else:
            trend = "mixed"  # 혼합
            
        return {
            "trend": trend,
            "dominant_emotion": recent_emotion,
            "is_stable": stability >= 0.7,
            "is_improving": is_improving,
            "negative_ratio": negative_ratio,
            "anxiety_ratio": anxiety_ratio
        }

# 싱글톤 인스턴스
_emotion_tracker = None

def get_emotion_tracker(db_client=None) -> EmotionTracker:
    """감정 추적기 싱글톤 인스턴스 반환"""
    global _emotion_tracker
    if _emotion_tracker is None:
        _emotion_tracker = EmotionTracker(db_client)
    return _emotion_tracker

# 기존 코드와의 호환성을 위한 함수
async def record_emotion(user_id: str, emotion_data: Dict[str, Any]) -> bool:
    """
    사용자의 감정 데이터를 기록 (호환성 함수)
    """
    tracker = get_emotion_tracker()
    return await tracker.record_emotion(user_id, emotion_data)
