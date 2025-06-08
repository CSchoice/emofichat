"""
데이터베이스 서비스

MySQL과 Redis를 활용하여 사용자 데이터, 감정 데이터, 대화 이력 등을 관리합니다.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, func, desc

from app.core.db import SessionMaker
from app.core.cache import get_session_manager, get_emotion_cache, get_product_cache
from app.models.database import (
    User, EmotionRecord, Conversation, Message, 
    FinancialProfile, RiskEvaluation, Product, Recommendation
)

logger = logging.getLogger(__name__)


class DatabaseService:
    """데이터베이스 서비스 클래스"""
    
    def __init__(self):
        self.session_manager = get_session_manager()
        self.emotion_cache = get_emotion_cache()
        self.product_cache = get_product_cache()
    
    async def get_db_session(self) -> AsyncSession:
        """데이터베이스 세션 가져오기"""
        return SessionMaker()
    
    # 사용자 관련 메서드
    async def get_or_create_user(self, user_id: str) -> User:
        """사용자 조회 또는 생성"""
        async with await self.get_db_session() as session:
            # 사용자 조회
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalars().first()
            
            # 사용자가 없으면 생성
            if not user:
                user = User(user_id=user_id)
                session.add(user)
                await session.commit()
                await session.refresh(user)
                logger.info(f"새 사용자 생성: {user_id}")
            
            return user
    
    async def get_any_user(self) -> Optional[User]:
        """데이터베이스에서 아무 사용자나 한 명 조회"""
        async with await self.get_db_session() as session:
            result = await session.execute(
                select(User).limit(1)
            )
            return result.scalars().first()
    
    async def list_users(self, limit: int = 10) -> List[User]:
        """데이터베이스에서 사용자 목록 조회"""
        async with await self.get_db_session() as session:
            result = await session.execute(
                select(User).limit(limit)
            )
            return list(result.scalars().all())
    
    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """사용자 정보 업데이트"""
        async with await self.get_db_session() as session:
            # 사용자 조회
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalars().first()
            
            if not user:
                return False
            
            # 업데이트할 필드 설정
            for key, value in user_data.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            await session.commit()
            return True
    
    # 감정 기록 관련 메서드
    async def save_emotion_record(self, user_id: str, message: str, emotion_data: Dict[str, Any]) -> EmotionRecord:
        """감정 기록 저장"""
        async with await self.get_db_session() as session:
            # 감정 기록 생성
            emotion_record = EmotionRecord(
                user_id=user_id,
                message=message,
                dominant_emotion=emotion_data.get("dominant_emotion", "중립"),
                dominant_score=emotion_data.get("dominant_score", 0.0),
                is_negative=emotion_data.get("is_negative", False),
                is_anxious=emotion_data.get("is_anxious", False),
                all_emotions=emotion_data.get("all_emotions", {})
            )
            
            session.add(emotion_record)
            await session.commit()
            await session.refresh(emotion_record)
            
            # Redis 캐시에도 저장
            await self.emotion_cache.cache_emotion(user_id, emotion_data)
            
            return emotion_record
    
    async def get_emotion_history(self, user_id: str, limit: int = 10) -> List[EmotionRecord]:
        """감정 기록 이력 조회"""
        async with await self.get_db_session() as session:
            result = await session.execute(
                select(EmotionRecord)
                .where(EmotionRecord.user_id == user_id)
                .order_by(desc(EmotionRecord.recorded_at))
                .limit(limit)
            )
            
            return list(result.scalars().all())
    
    async def get_emotion_trend(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """감정 트렌드 분석"""
        # 먼저 Redis 캐시에서 조회 시도
        cached_trend = await self.emotion_cache.get_emotion_trend(user_id, days)
        if cached_trend and cached_trend.get("data_points", 0) > 0:
            return cached_trend
        
        # 캐시에 없으면 데이터베이스에서 조회
        async with await self.get_db_session() as session:
            # 특정 기간 내의 감정 기록 조회
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            result = await session.execute(
                select(EmotionRecord)
                .where(
                    EmotionRecord.user_id == user_id,
                    EmotionRecord.recorded_at >= cutoff_date
                )
                .order_by(EmotionRecord.recorded_at)
            )
            
            records = list(result.scalars().all())
            
            if not records:
                return {
                    "user_id": user_id,
                    "days": days,
                    "data_points": 0,
                    "message": "감정 데이터가 충분하지 않습니다."
                }
            
            # 감정 빈도 계산
            emotion_frequency = {}
            for record in records:
                emotion = record.dominant_emotion
                emotion_frequency[emotion] = emotion_frequency.get(emotion, 0) + 1
            
            # 가장 빈번한 감정 찾기
            most_frequent = max(emotion_frequency.items(), key=lambda x: x[1])
            
            # 부정/불안 비율 계산
            negative_count = sum(1 for r in records if r.is_negative)
            anxious_count = sum(1 for r in records if r.is_anxious)
            
            # 감정 변동성 계산
            volatility = 0
            prev_emotion = None
            for record in records:
                curr_emotion = record.dominant_emotion
                if prev_emotion and curr_emotion != prev_emotion:
                    volatility += 1
                prev_emotion = curr_emotion
            
            # 정규화된 변동성 (0~1 사이)
            norm_volatility = volatility / (len(records) - 1) if len(records) > 1 else 0
            
            trend_data = {
                "user_id": user_id,
                "days": days,
                "data_points": len(records),
                "most_frequent_emotion": most_frequent[0],
                "emotion_frequency": emotion_frequency,
                "negative_ratio": negative_count / len(records),
                "anxious_ratio": anxious_count / len(records),
                "emotion_volatility": norm_volatility
            }
            
            return trend_data
    
    # 대화 관련 메서드
    async def create_conversation(self, user_id: str) -> Tuple[Conversation, str]:
        """새 대화 세션 생성"""
        async with await self.get_db_session() as session:
            # 세션 ID 생성
            timestamp = int(datetime.utcnow().timestamp())
            session_id = f"{timestamp}_{user_id}"
            
            # 대화 세션 생성
            conversation = Conversation(
                user_id=user_id,
                session_id=session_id
            )
            
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)
            
            # Redis 세션 생성
            await self.session_manager.create_session(
                user_id, 
                {
                    "conversation_id": conversation.id,
                    "session_id": session_id,
                    "state": "initial"
                }
            )
            
            return conversation, session_id
    
    async def get_conversation(self, session_id: str) -> Optional[Conversation]:
        """대화 세션 조회"""
        # Redis 세션 조회
        session_data = await self.session_manager.get_session(session_id)
        if not session_data:
            return None
        
        conversation_id = session_data.get("conversation_id")
        if not conversation_id:
            return None
        
        # 데이터베이스에서 대화 세션 조회
        async with await self.get_db_session() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            
            return result.scalars().first()
    
    async def end_conversation(self, session_id: str) -> bool:
        """대화 세션 종료"""
        # Redis 세션 종료
        await self.session_manager.end_session(session_id)
        
        # 데이터베이스 세션 종료
        session_data = await self.session_manager.get_session(session_id)
        if not session_data:
            return False
        
        conversation_id = session_data.get("conversation_id")
        if not conversation_id:
            return False
        
        async with await self.get_db_session() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            
            conversation = result.scalars().first()
            if not conversation:
                return False
            
            # 종료 시간 설정
            conversation.ended_at = datetime.utcnow()
            await session.commit()
            
            return True
    
    async def save_message(
        self, 
        conversation_id: int, 
        content: str, 
        is_user: bool = True,
        emotion_record_id: Optional[int] = None,
        state: Optional[str] = None
    ) -> Message:
        """메시지 저장"""
        async with await self.get_db_session() as session:
            # 메시지 생성
            message = Message(
                conversation_id=conversation_id,
                is_user=is_user,
                content=content,
                emotion_record_id=emotion_record_id,
                state=state
            )
            
            session.add(message)
            await session.commit()
            await session.refresh(message)
            
            return message
    
    async def get_conversation_history(self, conversation_id: int, limit: int = 20) -> List[Message]:
        """대화 이력 조회"""
        async with await self.get_db_session() as session:
            result = await session.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.sent_at)
                .limit(limit)
            )
            
            return list(result.scalars().all())
    
    # 재무 프로필 관련 메서드
    async def get_or_create_financial_profile(self, user_id: str) -> FinancialProfile:
        """재무 프로필 조회 또는 생성"""
        async with await self.get_db_session() as session:
            # 재무 프로필 조회
            result = await session.execute(
                select(FinancialProfile).where(FinancialProfile.user_id == user_id)
            )
            profile = result.scalars().first()
            
            # 프로필이 없으면 생성
            if not profile:
                profile = FinancialProfile(user_id=user_id)
                session.add(profile)
                await session.commit()
                await session.refresh(profile)
                logger.info(f"새 재무 프로필 생성: {user_id}")
            
            return profile
    
    async def update_financial_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """재무 프로필 업데이트"""
        async with await self.get_db_session() as session:
            # 재무 프로필 조회
            result = await session.execute(
                select(FinancialProfile).where(FinancialProfile.user_id == user_id)
            )
            profile = result.scalars().first()
            
            if not profile:
                return False
            
            # 업데이트할 필드 설정
            for key, value in profile_data.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            
            await session.commit()
            return True
    
    async def save_risk_evaluation(self, financial_profile_id: int, risk_data: Dict[str, Any]) -> RiskEvaluation:
        """위험 평가 저장"""
        async with await self.get_db_session() as session:
            # 위험 평가 생성
            risk_evaluation = RiskEvaluation(
                financial_profile_id=financial_profile_id,
                financial_stress_index=risk_data.get("financial_stress_index", 0.0),
                stress_trend=risk_data.get("stress_trend", "stable"),
                evaluation_factors=risk_data.get("evaluation_factors", {})
            )
            
            session.add(risk_evaluation)
            await session.commit()
            await session.refresh(risk_evaluation)
            
            return risk_evaluation
    
    # 금융 상품 관련 메서드
    async def get_products_by_type(self, product_type: str, limit: int = 10) -> List[Product]:
        """상품 유형별 조회"""
        # 먼저 Redis 캐시에서 조회 시도
        cached_product_ids = await self.product_cache.get_products_by_type(product_type, limit)
        
        if cached_product_ids:
            products = []
            for product_id in cached_product_ids:
                cached_product = await self.product_cache.get_product(product_id)
                if cached_product:
                    products.append(cached_product)
            
            if len(products) >= limit:
                return products
        
        # 캐시에 없거나 부족하면 데이터베이스에서 조회
        async with await self.get_db_session() as session:
            result = await session.execute(
                select(Product)
                .where(Product.type == product_type)
                .limit(limit)
            )
            
            products = list(result.scalars().all())
            
            # 캐시에 저장
            for product in products:
                product_data = {
                    "id": product.id,
                    "product_id": product.product_id,
                    "name": product.name,
                    "type": product.type,
                    "description": product.description,
                    "interest_rate": product.interest_rate,
                    "min_period": product.min_period,
                    "max_period": product.max_period,
                    "min_amount": product.min_amount,
                    "risk_level": product.risk_level,
                    "features": product.features
                }
                await self.product_cache.cache_product(product.product_id, product_data)
            
            return products
    
    async def save_recommendation(
        self, 
        user_id: str, 
        product_id: int, 
        score: float,
        explanation: Optional[str] = None,
        conversation_id: Optional[int] = None
    ) -> Recommendation:
        """추천 기록 저장"""
        async with await self.get_db_session() as session:
            # 추천 기록 생성
            recommendation = Recommendation(
                user_id=user_id,
                product_id=product_id,
                conversation_id=conversation_id,
                score=score,
                explanation=explanation
            )
            
            session.add(recommendation)
            await session.commit()
            await session.refresh(recommendation)
            
            return recommendation
    
    async def get_user_recommendations(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """사용자 추천 이력 조회"""
        async with await self.get_db_session() as session:
            # 추천 기록과 상품 정보 조인 조회
            result = await session.execute(
                select(Recommendation, Product)
                .join(Product, Recommendation.product_id == Product.id)
                .where(Recommendation.user_id == user_id)
                .order_by(desc(Recommendation.recommended_at))
                .limit(limit)
            )
            
            recommendations = []
            for rec, product in result:
                recommendations.append({
                    "id": rec.id,
                    "product_id": product.product_id,
                    "product_name": product.name,
                    "product_type": product.type,
                    "score": rec.score,
                    "explanation": rec.explanation,
                    "recommended_at": rec.recommended_at.isoformat(),
                    "is_clicked": rec.is_clicked
                })
            
            return recommendations


# 싱글톤 인스턴스
_db_service = None


def get_db_service() -> DatabaseService:
    """데이터베이스 서비스 싱글톤 인스턴스 반환"""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service
