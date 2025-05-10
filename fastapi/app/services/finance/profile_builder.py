"""
사용자 재무 프로필 생성기

사용자의 재무 데이터와 감정 상태를 바탕으로 사용자 프로필을 생성합니다.
"""

import logging
from typing import Dict, Any, List, Optional

from app.services.finance.analyzer import get_finance_analyzer

# 로거 설정
logger = logging.getLogger(__name__)

class FinanceProfileBuilder:
    """사용자 재무 프로필 생성 클래스"""
    
    def __init__(self, db_client=None):
        self.db = db_client
        self.finance_analyzer = get_finance_analyzer()
        
    def infer_user_profile(
        self,
        row: Dict[str, Any],
        finance_trends: Dict[str, Any],
        conversation_history: str,
        user_msg: str,
        emotion_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        사용자의 재무 데이터와 감정 상태를 바탕으로 프로필 추론
        
        Args:
            row: 사용자 재무 데이터
            finance_trends: 재무 추세 분석 결과
            conversation_history: 대화 이력
            user_msg: 사용자 메시지
            emotion_data: 감정 분석 결과
            
        Returns:
            사용자 프로필
        """
        profile: Dict[str, Any] = {}
        
        try:
            # 재무성향
            if row.get("liquidity_score", 50) > 70 and finance_trends.get("balance_trend") == "지속 증가":
                profile["재무성향"] = "보수적 소비자"
            elif row.get("card_usage_b0m", 0) > row.get("avg_balance_3m", 0) * 1.2:
                profile["재무성향"] = "과소비 경향"
            else:
                profile["재무성향"] = "일반 소비자"
                
            # 금융단계
            age = row.get("age", 35)
            if age < 30:
                profile["금융단계"] = "사회초년생"
            elif age < 45:
                profile["금융단계"] = "자산형성기"
            elif age < 55:
                profile["금융단계"] = "자녀양육기"
            else:
                profile["금융단계"] = "은퇴준비기"
                
            # 스트레스반응
            dom = emotion_data.get("dominant_emotion", "중립")
            if dom in ("화남", "슬픔", "공포", "걱정"):
                profile["스트레스반응"] = f"{dom} 감정에 따른 대응"
            else:
                profile["스트레스반응"] = "문제 자체 해결 성향"
                
            # 위험 감수성
            risk_tolerance = "중간"
            if profile["재무성향"] == "보수적 소비자":
                risk_tolerance = "낮음"
            elif profile["재무성향"] == "과소비 경향":
                risk_tolerance = "높음"
            profile["위험감수성"] = risk_tolerance
            
            # 재무 목표
            if "금융단계" in profile:
                if profile["금융단계"] == "사회초년생":
                    profile["재무목표"] = "자산 형성 및 부채 관리"
                elif profile["금융단계"] == "자산형성기":
                    profile["재무목표"] = "자산 증식 및 안정적 투자"
                elif profile["금융단계"] == "자녀양육기":
                    profile["재무목표"] = "교육비 마련 및 은퇴 준비"
                else:
                    profile["재무목표"] = "안정적 노후 자금 확보"
            
            # 투자 성향
            investment_style = "안정 추구형"
            if risk_tolerance == "높음":
                investment_style = "공격 투자형"
            elif risk_tolerance == "중간":
                investment_style = "균형 투자형"
            profile["투자성향"] = investment_style
            
            # 소비 패턴
            if "card_usage_trend" in finance_trends:
                if finance_trends["card_usage_trend"] == "증가 추세":
                    profile["소비패턴"] = "증가 추세"
                elif finance_trends["card_usage_trend"] == "감소 추세":
                    profile["소비패턴"] = "감소 추세"
                else:
                    profile["소비패턴"] = "안정적"
            
            # 저축 성향
            if "balance_trend" in finance_trends:
                if finance_trends["balance_trend"] == "지속 증가":
                    profile["저축성향"] = "적극적 저축형"
                elif finance_trends["balance_trend"] == "감소 추세":
                    profile["저축성향"] = "소비 중심형"
                else:
                    profile["저축성향"] = "균형형"
            
            return profile
            
        except Exception as e:
            logger.error(f"사용자 프로필 추론 중 오류 발생: {str(e)}")
            # 기본 프로필 반환
            return {
                "재무성향": "일반 소비자",
                "금융단계": "자산형성기",
                "스트레스반응": "문제 자체 해결 성향",
                "위험감수성": "중간",
                "재무목표": "자산 증식 및 안정적 투자",
                "투자성향": "균형 투자형",
                "소비패턴": "안정적",
                "저축성향": "균형형"
            }
    
    async def save_profile(self, user_id: str, profile: Dict[str, Any]) -> bool:
        """
        사용자 프로필 저장
        
        Args:
            user_id: 사용자 ID
            profile: 사용자 프로필
            
        Returns:
            저장 성공 여부
        """
        try:
            # DB 연결이 있는 경우 DB에 저장
            if self.db:
                await self.db.user_profiles.update_one(
                    {"user_id": user_id},
                    {"$set": profile},
                    upsert=True
                )
                logger.debug(f"사용자 프로필 DB 저장 완료: {user_id}")
                return True
            else:
                # DB 연결이 없는 경우 로그만 남김
                logger.info(f"사용자 프로필 저장 (DB 없음): {user_id}, {profile}")
                return True
                
        except Exception as e:
            logger.error(f"사용자 프로필 저장 실패: {str(e)}")
            return False
    
    async def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        사용자 프로필 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            사용자 프로필
        """
        try:
            # DB 연결이 있는 경우 DB에서 조회
            if self.db:
                profile = await self.db.user_profiles.find_one({"user_id": user_id})
                return profile
            else:
                # DB 연결이 없는 경우 None 반환
                logger.info(f"사용자 프로필 조회 (DB 없음): {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"사용자 프로필 조회 실패: {str(e)}")
            return None
    
    async def update_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        사용자 프로필 업데이트
        
        Args:
            user_id: 사용자 ID
            updates: 업데이트할 필드
            
        Returns:
            업데이트 성공 여부
        """
        try:
            # DB 연결이 있는 경우 DB에서 업데이트
            if self.db:
                result = await self.db.user_profiles.update_one(
                    {"user_id": user_id},
                    {"$set": updates}
                )
                return result.modified_count > 0
            else:
                # DB 연결이 없는 경우 로그만 남김
                logger.info(f"사용자 프로필 업데이트 (DB 없음): {user_id}, {updates}")
                return True
                
        except Exception as e:
            logger.error(f"사용자 프로필 업데이트 실패: {str(e)}")
            return False

# 싱글톤 인스턴스
_profile_builder = None

def get_profile_builder(db_client=None) -> FinanceProfileBuilder:
    """사용자 프로필 생성기 싱글톤 인스턴스 반환"""
    global _profile_builder
    if _profile_builder is None:
        _profile_builder = FinanceProfileBuilder(db_client)
    return _profile_builder

# 기존 코드와의 호환성을 위한 함수
def infer_user_profile(
    row: Dict[str, Any],
    finance_trends: Dict[str, Any],
    conversation_history: str,
    user_msg: str,
    emotion_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    사용자의 재무 데이터와 감정 상태를 바탕으로 프로필 추론 (호환성 함수)
    """
    profile_builder = get_profile_builder()
    return profile_builder.infer_user_profile(
        row, finance_trends, conversation_history, user_msg, emotion_data
    )
