"""
대화 상태 관리자

사용자와의 대화 상태를 관리하고 추적합니다.
"""

import logging
import json
import enum
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# 로거 설정
logger = logging.getLogger(__name__)

class ConversationState(enum.Enum):
    """대화 상태 열거형"""
    GREETING = "greeting"                      # 인사
    EMOTION_ASSESSMENT = "emotion_assessment"  # 감정 평가
    FINANCE_ASSESSMENT = "finance_assessment"  # 재무 평가
    GENERAL_ADVICE = "general_advice"          # 일반 조언
    PRODUCT_RECOMMENDATION = "product_recommendation"  # 상품 추천
    RISK_WARNING = "risk_warning"              # 위험 경고
    FOLLOWUP = "followup"                      # 후속 조치

class ConversationStateManager:
    """대화 상태 관리 클래스"""
    
    def __init__(self, db_client=None):
        self.db = db_client
        
    async def get_state(self, user_id: str) -> Dict[str, Any]:
        """
        사용자의 현재 대화 상태 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            대화 상태 정보
        """
        try:
            # DB 연결이 있는 경우 DB에서 조회
            if self.db:
                state = await self.db.conversation_states.find_one({"user_id": user_id})
                if state:
                    return state
            
            # 상태가 없는 경우 기본 상태 생성
            return self._create_default_state(user_id)
            
        except Exception as e:
            logger.error(f"대화 상태 조회 실패: {str(e)}")
            return self._create_default_state(user_id)
            
    async def update_state(self, user_id: str, new_state: Dict[str, Any]) -> bool:
        """
        사용자의 대화 상태 업데이트
        
        Args:
            user_id: 사용자 ID
            new_state: 새로운 상태 정보
            
        Returns:
            업데이트 성공 여부
        """
        try:
            # 업데이트할 데이터 구성
            update_data = {
                "last_updated": datetime.now(),
                **new_state
            }
            
            # DB 연결이 있는 경우 DB에 저장
            if self.db:
                result = await self.db.conversation_states.update_one(
                    {"user_id": user_id},
                    {"$set": update_data},
                    upsert=True
                )
                logger.debug(f"대화 상태 DB 저장 완료: {user_id}")
                return result.acknowledged
            else:
                # DB 연결이 없는 경우 로그만 남김
                logger.info(f"대화 상태 업데이트 (DB 없음): {user_id}, {json.dumps(update_data)}")
                return True
                
        except Exception as e:
            logger.error(f"대화 상태 업데이트 실패: {str(e)}")
            return False
            
    async def transition_state(
        self, 
        user_id: str, 
        current_state: str, 
        emotion_data: Dict[str, Any], 
        finance_data: Dict[str, Any]
    ) -> Tuple[str, List[str]]:
        """
        대화 상태 전이 결정
        
        Args:
            user_id: 사용자 ID
            current_state: 현재 상태
            emotion_data: 감정 분석 결과
            finance_data: 재무 분석 결과
            
        Returns:
            (다음 상태, 필요한 액션 목록)
        """
        # 현재 상태가 없으면 인사 상태로 시작
        if not current_state:
            return ConversationState.GREETING.value, ["greet"]
            
        # 감정 상태 확인
        is_negative = emotion_data.get("is_negative", False)
        is_anxious = emotion_data.get("is_anxious", False)
        dominant_emotion = emotion_data.get("dominant_emotion", "중립")
        
        # 재무 상태 확인
        is_delinquent = finance_data.get("is_delinquent", False)
        stress_index = finance_data.get("stress_index", 0)
        
        # 위험 상태 확인 (감정 + 재무)
        is_at_risk = is_delinquent or stress_index > 70 or (is_negative and is_anxious)
        
        # 상태 전이 로직
        next_state = current_state
        actions = []
        
        # 현재 상태별 전이 로직
        if current_state == ConversationState.GREETING.value:
            # 인사 상태에서는 감정 평가로 전이
            next_state = ConversationState.EMOTION_ASSESSMENT.value
            actions.append("assess_emotion")
            
        elif current_state == ConversationState.EMOTION_ASSESSMENT.value:
            # 감정 평가 상태에서는 재무 평가 또는 위험 경고로 전이
            if is_at_risk:
                next_state = ConversationState.RISK_WARNING.value
                actions.append("warn_risk")
            else:
                next_state = ConversationState.FINANCE_ASSESSMENT.value
                actions.append("assess_finance")
                
        elif current_state == ConversationState.FINANCE_ASSESSMENT.value:
            # 재무 평가 상태에서는 일반 조언 또는 상품 추천으로 전이
            if "추천" in finance_data.get("keywords", []):
                next_state = ConversationState.PRODUCT_RECOMMENDATION.value
                actions.append("recommend_product")
            else:
                next_state = ConversationState.GENERAL_ADVICE.value
                actions.append("provide_advice")
                
        elif current_state == ConversationState.GENERAL_ADVICE.value:
            # 일반 조언 상태에서는 후속 조치로 전이
            next_state = ConversationState.FOLLOWUP.value
            actions.append("followup")
            
        elif current_state == ConversationState.PRODUCT_RECOMMENDATION.value:
            # 상품 추천 상태에서는 후속 조치로 전이
            next_state = ConversationState.FOLLOWUP.value
            actions.append("followup")
            
        elif current_state == ConversationState.RISK_WARNING.value:
            # 위험 경고 상태에서는 재무 평가로 전이
            next_state = ConversationState.FINANCE_ASSESSMENT.value
            actions.append("assess_finance")
            
        elif current_state == ConversationState.FOLLOWUP.value:
            # 후속 조치 상태에서는 감정 평가로 전이
            next_state = ConversationState.EMOTION_ASSESSMENT.value
            actions.append("assess_emotion")
            
        # 위험 상태가 감지되면 언제든지 위험 경고로 전이
        if is_at_risk and next_state != ConversationState.RISK_WARNING.value:
            next_state = ConversationState.RISK_WARNING.value
            actions = ["warn_risk"]
            
        # 상태 변경 로깅
        logger.info(f"대화 상태 전이: {current_state} -> {next_state}, 액션: {actions}")
        
        return next_state, actions
        
    def _create_default_state(self, user_id: str) -> Dict[str, Any]:
        """기본 대화 상태 생성"""
        return {
            "user_id": user_id,
            "current_state": ConversationState.GREETING.value,
            "previous_state": None,
            "conversation_count": 0,
            "last_updated": datetime.now(),
            "actions": ["greet"],
            "context": {}
        }

# 싱글톤 인스턴스
_state_manager = None

def get_state_manager(db_client=None) -> ConversationStateManager:
    """대화 상태 관리자 싱글톤 인스턴스 반환"""
    global _state_manager
    if _state_manager is None:
        _state_manager = ConversationStateManager(db_client)
    return _state_manager
