"""
통합 상담 서비스

감정 분석, 대화 관리, 재무 분석, 추천 시스템 등 모든 컴포넌트를 통합하여
전체 상담 흐름을 조정합니다.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple

from app.services.emotion.classifier import get_emotion_classifier
from app.services.emotion.tracker import get_emotion_tracker
from app.services.conversation.state_manager import get_state_manager, ConversationState
from app.services.conversation.flow_engine import get_flow_engine
from app.services.conversation.history import get_history_manager
from app.services.finance.analyzer import get_finance_analyzer
from app.services.finance.risk_evaluator import get_risk_evaluator
from app.services.finance.profile_builder import get_profile_builder
from app.services.recommendation.product_matcher import get_product_matcher, PRODUCT_TYPE_DEPOSIT, PRODUCT_TYPE_FUND
from app.services.recommendation.explanation_generator import get_explanation_generator
from app.services.recommendation.formatter import get_recommendation_formatter
from app.core.openai_client import client as openai_client

# 로거 설정
logger = logging.getLogger(__name__)

# GPT 모델 설정
GPT_MODEL = "gpt-3.5-turbo-0125"
GPT_TEMPERATURE = 0.5
GPT_MAX_TOKENS = 1500

class AdvisorService:
    """통합 상담 서비스 클래스"""
    
    def __init__(self, db_client=None, llm_client=None):
        # 컴포넌트 초기화
        self.emotion_classifier = get_emotion_classifier()
        self.emotion_tracker = get_emotion_tracker(db_client)
        self.state_manager = get_state_manager(db_client)
        self.flow_engine = get_flow_engine(db_client)
        self.history_manager = get_history_manager(db_client)
        self.finance_analyzer = get_finance_analyzer()
        self.risk_evaluator = get_risk_evaluator()
        self.profile_builder = get_profile_builder(db_client)
        self.product_matcher = get_product_matcher(db_client)
        self.explanation_generator = get_explanation_generator(llm_client or openai_client)
        self.recommendation_formatter = get_recommendation_formatter()
        
        # 클라이언트 설정
        self.db = db_client
        self.llm_client = llm_client or openai_client
        
    async def process_message(self, user_id: str, message: str) -> Dict[str, Any]:
        """
        사용자 메시지 처리 및 응답 생성
        
        Args:
            user_id: 사용자 ID
            message: 사용자 메시지
            
        Returns:
            응답 데이터
        """
        try:
            # 1. 병렬 처리를 위한 태스크 생성
            emotion_task = asyncio.create_task(self._analyze_emotion(message))
            finance_task = asyncio.create_task(self._get_finance_data(user_id))
            state_task = asyncio.create_task(self.state_manager.get_state(user_id))
            history_task = asyncio.create_task(self.history_manager.load_history(user_id))
            
            # 2. 모든 태스크 완료 대기
            emotion_data, finance_data, state, history = await asyncio.gather(
                emotion_task, finance_task, state_task, history_task
            )
            
            # 3. 대화 흐름 처리
            flow_result, state_update = await self.flow_engine.process(
                user_id, message, emotion_data, finance_data
            )
            
            # 4. 사용자 프로필 업데이트
            profile_task = asyncio.create_task(self._update_user_profile(
                user_id, finance_data, history, message, emotion_data
            ))
            
            # 5. 응답 생성 전략 결정
            if "recommend_product" in flow_result.get("actions", []):
                # 상품 추천 응답
                response = await self._generate_product_recommendation(
                    user_id, finance_data, emotion_data, message
                )
            else:
                # 일반 상담 응답
                response = await self._generate_conversation_response(
                    user_id, message, emotion_data, finance_data, flow_result, history
                )
            
            # 6. 대화 이력 저장
            history_task = asyncio.create_task(
                self.history_manager.save_history(user_id, message, response)
            )
            
            # 7. 응답 데이터 구성
            result = {
                "reply": response,
                "emotion": emotion_data,
                "state": flow_result.get("state"),
                "actions": flow_result.get("actions", [])
            }
            
            # 8. 위험 평가 결과가 있는 경우 추가
            if "warn_risk" in flow_result.get("actions", []):
                risk_result = self.risk_evaluator.evaluate_risk(finance_data, emotion_data)
                if risk_result.get("warning_needed", False):
                    result["risk_warning"] = risk_result
            
            # 프로필 태스크 완료 대기 (결과는 사용하지 않음)
            await profile_task
            
            return result
            
        except Exception as e:
            logger.error(f"메시지 처리 중 오류 발생: {str(e)}")
            return {
                "reply": "죄송합니다. 메시지 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                "error": str(e)
            }
    
    async def _analyze_emotion(self, message: str) -> Dict[str, Any]:
        """
        감정 분석 수행
        
        Args:
            message: 사용자 메시지
            
        Returns:
            감정 분석 결과
        """
        try:
            return self.emotion_classifier.analyze_emotion(message)
        except Exception as e:
            logger.error(f"감정 분석 중 오류 발생: {str(e)}")
            return {
                "dominant_emotion": "중립",
                "dominant_score": 1.0,
                "is_negative": False,
                "is_anxious": False,
                "all_emotions": {}
            }
    
    async def _get_finance_data(self, user_id: str) -> Dict[str, Any]:
        """
        사용자 재무 데이터 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            재무 데이터
        """
        try:
            # 실제 구현에서는 DB에서 사용자 재무 데이터 조회
            # 여기서는 샘플 데이터 반환
            return {
                "user_id": user_id,
                "age": 35,
                "gender": "남성",
                "balance_b0m": 5000000,
                "balance_b1m": 4800000,
                "balance_b2m": 4600000,
                "avg_balance_3m": 4800000,
                "card_usage_b0m": 1500000,
                "card_usage_b1m": 1400000,
                "card_usage_b2m": 1300000,
                "is_delinquent": False,
                "liquidity_score": 65
            }
        except Exception as e:
            logger.error(f"재무 데이터 조회 중 오류 발생: {str(e)}")
            return {
                "user_id": user_id,
                "balance_b0m": 0,
                "is_delinquent": False
            }
    
    async def _update_user_profile(
        self,
        user_id: str,
        finance_data: Dict[str, Any],
        history: List[Tuple[str, str]],
        message: str,
        emotion_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        사용자 프로필 업데이트
        
        Args:
            user_id: 사용자 ID
            finance_data: 재무 데이터
            history: 대화 이력
            message: 사용자 메시지
            emotion_data: 감정 분석 결과
            
        Returns:
            업데이트된 프로필
        """
        try:
            # 재무 추세 분석
            finance_trends = self.finance_analyzer.analyze_financial_trends(finance_data)
            
            # 대화 이력 요약
            history_summary = await self.history_manager.get_summary(user_id)
            
            # 사용자 프로필 추론
            profile = self.profile_builder.infer_user_profile(
                finance_data, finance_trends, history_summary, message, emotion_data
            )
            
            # 프로필 저장
            await self.profile_builder.save_profile(user_id, profile)
            
            return profile
            
        except Exception as e:
            logger.error(f"사용자 프로필 업데이트 중 오류 발생: {str(e)}")
            return {}
    
    async def _generate_product_recommendation(
        self,
        user_id: str,
        finance_data: Dict[str, Any],
        emotion_data: Dict[str, Any],
        message: str
    ) -> str:
        """
        상품 추천 응답 생성
        
        Args:
            user_id: 사용자 ID
            finance_data: 재무 데이터
            emotion_data: 감정 분석 결과
            message: 사용자 메시지
            
        Returns:
            추천 응답
        """
        try:
            # 상품 유형 결정
            if any(x in message for x in ("펀드", "투자")):
                product_type = PRODUCT_TYPE_FUND
            else:
                product_type = PRODUCT_TYPE_DEPOSIT
            
            # 상품 추천
            products = await self.product_matcher.recommend_products(
                user_id, finance_data, emotion_data, product_type, limit=3
            )
            
            # 추천 상품이 없는 경우
            if not products:
                return self.recommendation_formatter.format_recommendation(
                    [], product_type, emotion_data
                )
            
            # 추천 근거 생성
            products_with_explanation = await self.explanation_generator.generate_explanations(
                products, finance_data, emotion_data, product_type
            )
            
            # 추천 결과 포맷팅
            return self.recommendation_formatter.format_recommendation(
                products_with_explanation, product_type, emotion_data
            )
            
        except Exception as e:
            logger.error(f"상품 추천 생성 중 오류 발생: {str(e)}")
            return "죄송합니다. 상품 추천 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
    
    async def _generate_conversation_response(
        self,
        user_id: str,
        message: str,
        emotion_data: Dict[str, Any],
        finance_data: Dict[str, Any],
        flow_result: Dict[str, Any],
        history: List[Tuple[str, str]]
    ) -> str:
        """
        일반 상담 응답 생성
        
        Args:
            user_id: 사용자 ID
            message: 사용자 메시지
            emotion_data: 감정 분석 결과
            finance_data: 재무 데이터
            flow_result: 대화 흐름 처리 결과
            history: 대화 이력
            
        Returns:
            상담 응답
        """
        try:
            # 현재 상태
            current_state = flow_result.get("state", ConversationState.GREETING.value)
            actions = flow_result.get("actions", [])
            
            # 시스템 프롬프트 생성
            system_prompt = self.flow_engine.build_system_prompt(
                {"current_state": current_state}, emotion_data, finance_data
            )
            
            # 위험 경고가 필요한 경우
            if "warn_risk" in actions:
                risk_result = self.risk_evaluator.evaluate_risk(finance_data, emotion_data)
                if risk_result.get("warning_needed", False):
                    warning_message = self.risk_evaluator.generate_warning_message(risk_result)
                    system_prompt += f"\n\n{warning_message}"
            
            # 사용자 컨텍스트 구성
            user_context = self._build_user_context(
                user_id, message, emotion_data, finance_data, history
            )
            
            # LLM 호출
            response = await self._call_llm(system_prompt, user_context)
            
            return response
            
        except Exception as e:
            logger.error(f"상담 응답 생성 중 오류 발생: {str(e)}")
            return "죄송합니다. 응답 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
    
    def _build_user_context(
        self,
        user_id: str,
        message: str,
        emotion_data: Dict[str, Any],
        finance_data: Dict[str, Any],
        history: List[Tuple[str, str]]
    ) -> str:
        """
        사용자 컨텍스트 구성
        
        Args:
            user_id: 사용자 ID
            message: 사용자 메시지
            emotion_data: 감정 분석 결과
            finance_data: 재무 데이터
            history: 대화 이력
            
        Returns:
            사용자 컨텍스트
        """
        # 재무 데이터 요약
        finance_summary = {
            "재무성향": "정보없음",
            "금융단계": "정보없음",
            "나이": finance_data.get("age", "정보없음"),
            "성별": finance_data.get("gender", "정보없음"),
            "현재잔액": finance_data.get("balance_b0m", 0),
            "3개월평균잔액": finance_data.get("avg_balance_3m", 0),
            "최근카드사용액": finance_data.get("card_usage_b0m", 0),
            "연체여부": bool(finance_data.get("is_delinquent", 0)),
            "감정상태": emotion_data.get("dominant_emotion", "중립"),
        }
        
        # 대화 이력 요약
        history_summary = ""
        if history:
            history_lines = []
            for i, (q, a) in enumerate(history[-3:]):  # 최근 3개 대화만 포함
                history_lines.append(f"대화 {i+1}: Q[{q}] / A[{a}]")
            history_summary = "\n".join(history_lines)
        
        # 컨텍스트 구성
        parts = [
            "[사용자 재무 데이터]",
            str(finance_summary),
            "[감정 상태]",
            f"주요 감정: {emotion_data.get('dominant_emotion', '중립')}",
            f"부정적 감정: {'예' if emotion_data.get('is_negative', False) else '아니오'}",
            f"불안 감정: {'예' if emotion_data.get('is_anxious', False) else '아니오'}"
        ]
        
        if history_summary:
            parts.extend(["[대화 이력]", history_summary])
            
        parts.extend(["[현재 질문]", message])
        
        return "\n".join(parts)
    
    async def _call_llm(self, system_prompt: str, user_content: str) -> str:
        """
        LLM 호출
        
        Args:
            system_prompt: 시스템 프롬프트
            user_content: 사용자 컨텍스트
            
        Returns:
            LLM 응답
        """
        try:
            # 메시지 구성
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
            
            # LLM 호출
            response = await self.llm_client.chat.completions.create(
                model=GPT_MODEL,
                temperature=GPT_TEMPERATURE,
                max_tokens=GPT_MAX_TOKENS,
                messages=messages
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"LLM 호출 중 오류 발생: {str(e)}")
            return "죄송합니다. 응답 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

# 싱글톤 인스턴스
_advisor_service = None

def get_advisor_service(db_client=None, llm_client=None) -> AdvisorService:
    """통합 상담 서비스 싱글톤 인스턴스 반환"""
    global _advisor_service
    if _advisor_service is None:
        _advisor_service = AdvisorService(db_client, llm_client)
    return _advisor_service
