"""
개선된 채팅 API 엔드포인트

새로운 모듈화된 아키텍처를 사용하여 채팅 요청을 처리합니다.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request, BackgroundTasks
from app.models import ChatRequest, ChatResponse, EmotionResult, ProductRecommendation, ScenarioResult
from app.services.integration.advisor_service import get_advisor_service
import logging
from typing import Optional, Dict, Any
import time

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat/v2", response_model=ChatResponse)
async def chat_improved(req: ChatRequest, request: Request, background_tasks: BackgroundTasks):
    """개선된 채팅 메시지 처리 엔드포인트
    
    통합 상담 서비스를 사용하여 사용자 메시지를 처리합니다.
    감정 분석, 대화 상태 관리, 재무 분석, 상품 추천 등을 통합적으로 처리합니다.
    """
    try:
        # 처리 시작 시간
        start_time = time.time()
        
        # 통합 상담 서비스 인스턴스 가져오기
        advisor_service = get_advisor_service()
        
        # 메시지 처리
        result = await advisor_service.process_message(req.user_id, req.message)
        
        # 처리 시간 계산
        process_time = time.time() - start_time
        logger.info(f"메시지 처리 시간: {process_time:.2f}초")
        
        # 감정 분석 결과 변환
        emotion_result = None
        if "emotion" in result:
            emotion_data = result["emotion"]
            emotion_result = EmotionResult(
                dominant_emotion=emotion_data.get("dominant_emotion", "중립"),
                dominant_score=emotion_data.get("dominant_score", 0.0),
                is_negative=emotion_data.get("is_negative", False),
                is_anxious=emotion_data.get("is_anxious", False),
                all_emotions=emotion_data.get("all_emotions", {})
            )
        
        # 시나리오 결과 변환
        scenario_result = None
        if "scenario" in result:
            scen = result["scenario"]
            scenario_result = ScenarioResult(
                label=scen.get("label", ""),
                probability=scen.get("probability", 0.0),
                key_metrics=scen.get("key_metrics", {})
            )
        
        # 상품 추천 결과 변환
        product_recommendation = None
        if "product_recommendation" in result:
            prod_rec = result["product_recommendation"]
            product_recommendation = ProductRecommendation(
                product_type=prod_rec.get("product_type", ""),
                products=prod_rec.get("products", [])
            )
        
        # 응답 구성
        response = ChatResponse(
            reply=result.get("reply", ""),
            emotion=emotion_result,
            scenario=scenario_result,
            product_recommendation=product_recommendation
        )
        
        # 로깅 (백그라운드 작업으로 처리)
        background_tasks.add_task(
            log_chat, 
            req, 
            response, 
            result.get("state", ""),
            process_time
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Chat error: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="내부 서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        )

async def log_chat(
    req: ChatRequest, 
    response: ChatResponse, 
    state: str,
    process_time: float
):
    """채팅 로깅 함수"""
    try:
        # 민감 정보 마스킹
        masked_user_id = req.user_id[:3] + "****" if len(req.user_id) > 5 else "***"
        
        # 감정 정보
        emotion_log = ""
        if response.emotion:
            emotion_log = f", emotion={response.emotion.dominant_emotion}"
        
        # 로깅
        logger.info(
            f"Chat V2: user={masked_user_id}, state={state}{emotion_log}, "
            f"msg_len={len(req.message)}, reply_len={len(response.reply)}, "
            f"time={process_time:.2f}s"
        )
    except Exception as e:
        logger.error(f"로깅 중 오류 발생: {str(e)}")
