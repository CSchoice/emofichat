"""
대화 흐름 엔진

대화 상태에 따라 적절한 응답을 생성하고 대화 흐름을 제어합니다.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import asyncio

from app.services.conversation.state_manager import get_state_manager, ConversationState
from app.services.emotion.classifier import get_emotion_classifier
from app.services.emotion.tracker import get_emotion_tracker

# 로거 설정
logger = logging.getLogger(__name__)

class ConversationFlowEngine:
    """대화 흐름 제어 클래스"""
    
    def __init__(self, db_client=None):
        self.state_manager = get_state_manager(db_client)
        self.emotion_classifier = get_emotion_classifier()
        self.emotion_tracker = get_emotion_tracker(db_client)
        
    async def process(
        self, 
        user_id: str, 
        message: str, 
        emotion_data: Dict[str, Any] = None, 
        finance_data: Dict[str, Any] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        사용자 메시지 처리 및 대화 흐름 제어
        
        Args:
            user_id: 사용자 ID
            message: 사용자 메시지
            emotion_data: 감정 분석 결과 (없으면 분석 수행)
            finance_data: 재무 분석 결과 (없으면 기본값 사용)
            
        Returns:
            (응답 데이터, 상태 데이터)
        """
        # 감정 분석 결과가 없으면 분석 수행
        if not emotion_data:
            emotion_data = self.emotion_classifier.analyze_emotion(message)
            
        # 감정 데이터 기록 (비동기)
        asyncio.create_task(self.emotion_tracker.record_emotion(user_id, emotion_data))
        
        # 재무 데이터가 없으면 기본값 사용
        if not finance_data:
            finance_data = {
                "is_delinquent": False,
                "stress_index": 0,
                "keywords": []
            }
            
        # 현재 대화 상태 조회
        state = await self.state_manager.get_state(user_id)
        current_state = state.get("current_state", ConversationState.GREETING.value)
        
        # 대화 상태 전이 결정
        next_state, actions = await self.state_manager.transition_state(
            user_id, current_state, emotion_data, finance_data
        )
        
        # 상태 업데이트
        state_update = {
            "current_state": next_state,
            "previous_state": current_state,
            "conversation_count": state.get("conversation_count", 0) + 1,
            "actions": actions,
            "context": {
                "last_message": message,
                "dominant_emotion": emotion_data.get("dominant_emotion", "중립"),
                "is_negative": emotion_data.get("is_negative", False),
                "is_anxious": emotion_data.get("is_anxious", False),
                "is_delinquent": finance_data.get("is_delinquent", False),
                "stress_index": finance_data.get("stress_index", 0)
            }
        }
        
        # 상태 업데이트 (비동기)
        asyncio.create_task(self.state_manager.update_state(user_id, state_update))
        
        # 응답 데이터 구성
        response_data = {
            "state": next_state,
            "actions": actions,
            "emotion": emotion_data,
            "finance": finance_data
        }
        
        return response_data, state_update
        
    def build_system_prompt(self, state: Dict[str, Any], emotion_data: Dict[str, Any], finance_data: Dict[str, Any]) -> str:
        """
        현재 상태에 맞는 시스템 프롬프트 생성
        
        Args:
            state: 대화 상태 정보
            emotion_data: 감정 분석 결과
            finance_data: 재무 분석 결과
            
        Returns:
            시스템 프롬프트
        """
        current_state = state.get("current_state", ConversationState.GREETING.value)
        
        # 기본 프롬프트
        base_prompt = (
            "너는 전문 재무 상담 챗봇이야. 사용자의 재무 데이터와 감정 상태를 종합해 "
            "구체적이고 실용적인 조언을 제공해야 해."
        )
        
        # 상태별 추가 프롬프트
        state_prompts = {
            ConversationState.GREETING.value: 
                "사용자에게 친절하게 인사하고, 어떤 도움이 필요한지 물어봐.",
                
            ConversationState.EMOTION_ASSESSMENT.value: 
                f"사용자의 감정 상태는 '{emotion_data.get('dominant_emotion', '중립')}'로 "
                f"{'부정적' if emotion_data.get('is_negative', False) else '긍정적'}이야. "
                "감정에 공감하면서 대화를 이어가.",
                
            ConversationState.FINANCE_ASSESSMENT.value: 
                "사용자의 재무 상황을 파악하기 위한 질문을 해. "
                "소득, 지출, 저축, 부채 등에 대해 물어봐.",
                
            ConversationState.GENERAL_ADVICE.value: 
                "사용자의 상황에 맞는 일반적인 재무 조언을 제공해. "
                "구체적이고 실용적인 조언이 좋아.",
                
            ConversationState.PRODUCT_RECOMMENDATION.value: 
                "사용자의 상황에 맞는 금융 상품을 추천해. "
                "각 상품의 특징과 장단점을 설명하고, 왜 이 상품이 적합한지 이유를 설명해.",
                
            ConversationState.RISK_WARNING.value: 
                "사용자의 재무 상태가 위험해. 경고성 있는 조언을 제공하고, "
                "상황을 개선하기 위한 구체적인 방법을 제안해.",
                
            ConversationState.FOLLOWUP.value: 
                "이전 대화를 바탕으로 후속 질문을 해. "
                "사용자가 더 필요한 정보가 있는지 확인해."
        }
        
        # 현재 상태에 맞는 프롬프트 선택
        state_prompt = state_prompts.get(current_state, "")
        
        # 위험 상태 확인
        is_at_risk = finance_data.get("is_delinquent", False) or finance_data.get("stress_index", 0) > 70
        
        # 위험 상태인 경우 추가 프롬프트
        risk_prompt = ""
        if is_at_risk:
            risk_prompt = " 현재 사용자의 재무 상태가 위험하니, 경고성 있는 조언을 해줘."
            
        # 최종 프롬프트 구성
        return f"{base_prompt} {state_prompt}{risk_prompt}"

# 싱글톤 인스턴스
_flow_engine = None

def get_flow_engine(db_client=None) -> ConversationFlowEngine:
    """대화 흐름 엔진 싱글톤 인스턴스 반환"""
    global _flow_engine
    if _flow_engine is None:
        _flow_engine = ConversationFlowEngine(db_client)
    return _flow_engine
