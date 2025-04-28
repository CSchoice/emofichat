from fastapi import APIRouter, HTTPException, Depends, status, Request, BackgroundTasks
from app.models import ChatRequest, ChatResponse, EmotionResult, ProductRecommendation, ScenarioResult
from app.services.topic_detector import is_finance_topic, analyze_emotion, analyze_message
from app.services.emotion_tracker import record_emotion
from app.services.generic_chat import get_generic_reply
from app.services.finance_chat import get_finance_reply
from app.services.product_recommender import PRODUCT_TYPE_DEPOSIT, PRODUCT_TYPE_FUND
import logging
from typing import Optional, Dict, List, Any
import time
import re

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter()

# 간단한 속도 제한 함수
def rate_limit(request: Request):
    # 실제 앱에서는 Redis 같은 분산 저장소를 사용하는 것이 좋습니다
    user_id = request.query_params.get("user_id") or request.client.host
    last_request = getattr(request.app.state, f"last_request_{user_id}", 0)
    
    if time.time() - last_request < 0.5:  # 0.5초 간격 제한
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests"
        )
    
    setattr(request.app.state, f"last_request_{user_id}", time.time())

# 요청 로깅 함수
async def log_chat(req: ChatRequest, response: ChatResponse, is_finance: bool, emotion_data: dict = None):
    # 민감 정보 마스킹 - 실제 환경에서는 더 정교한 처리 필요
    masked_user_id = req.user_id[:3] + "****" if len(req.user_id) > 5 else "***"
    
    # 감정 정보 포함 로깅
    emotion_log = ""
    if emotion_data and "dominant_emotion" in emotion_data:
        emotion_log = f", emotion={emotion_data['dominant_emotion']}"
    
    logger.info(
        f"Chat: user={masked_user_id}, type={'finance' if is_finance else 'general'}{emotion_log}, "
        f"msg_len={len(req.message)}, reply_len={len(response.reply)}"
    )

def extract_product_recommendation(reply: str) -> tuple[str, Optional[ProductRecommendation]]:
    """
    응답 텍스트에서 상품 추천 정보를 추출하고 텍스트와 구조화된 데이터로 분리합니다.
    
    Args:
        reply: 원본 응답 텍스트
        
    Returns:
        (기본 응답 텍스트, 추출된 상품 추천 정보)
    """
    # 상품 추천 섹션 판별 패턴
    recommendation_pattern = r'📌\s*\*\*(예금/적금|펀드)\s*상품\s*추천\*\*\s*\n\n(.*?)(?=해당\s*상품에\s*관심이|$)'
    
    # 상품 추천 섹션 검색
    match = re.search(recommendation_pattern, reply, re.DOTALL)
    if not match:
        return reply, None
    
    # 상품 추천 섹션 추출
    product_type_text = match.group(1)
    product_section = match.group(0)
    
    # 상품 유형 결정
    product_type = PRODUCT_TYPE_DEPOSIT if "예금" in product_type_text or "적금" in product_type_text else PRODUCT_TYPE_FUND
    
    # 원본 응답에서 상품 추천 섹션 제거
    clean_reply = reply.replace(product_section, "").strip()
    
    # 상품 목록 추출
    product_list = []
    
    if product_type == PRODUCT_TYPE_DEPOSIT:
        # 예금/적금 추천 패턴
        products_pattern = r'(\d+)\.\s*\*\*([^*]+)\*\*\s*\(([^)]+)\)\s*\n\s*-\s*상품유형:\s*([^\n]+)\s*\n\s*-\s*기본금리:\s*([^\n]+)(?:\s*\(최대\s*([^\n)]+)\))?\s*\n\s*-\s*계약기간:\s*([^\n]+)\s*\n\s*-\s*가입금액:\s*([^\n]+)'
        for p_match in re.finditer(products_pattern, product_section, re.DOTALL):
            product = {
                "상품명": p_match.group(2).strip(),
                "은행명": p_match.group(3).strip(),
                "상품유형": p_match.group(4).strip(),
                "기본금리": p_match.group(5).strip(),
                "계약기간": p_match.group(7).strip(),
                "가입금액": p_match.group(8).strip()
            }
            
            # 최대우대금리가 있는 경우
            if p_match.group(6):
                product["최대우대금리"] = p_match.group(6).strip()
                
            product_list.append(product)
    else:
        # 펀드 추천 패턴
        products_pattern = r'(\d+)\.\s*\*\*([^*]+)\*\*\s*\(([^)]+)\)\s*\n\s*-\s*유형:\s*([^\n]+)\s*\n\s*-\s*수익률:\s*([^\n]+)\s*\n\s*-\s*위험등급:\s*([^\n]+)'
        for p_match in re.finditer(products_pattern, product_section, re.DOTALL):
            product = {
                "펀드명": p_match.group(2).strip(),
                "운용사": p_match.group(3).strip(),
                "유형": p_match.group(4).strip(),
                "수익률": p_match.group(5).strip(),
                "위험등급": p_match.group(6).strip()
            }
            product_list.append(product)
    
    # 추출한 상품이 없으면 None 반환
    if not product_list:
        return reply, None
    
    return clean_reply, ProductRecommendation(product_type=product_type, products=product_list)

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request, background_tasks: BackgroundTasks):
    """채팅 메시지 처리 엔드포인트
    
    금융 관련 메시지인지 판단하여 적절한 서비스로 라우팅합니다.
    감정 분석을 함께 수행하여 맞춤형 응답을 제공합니다.
    필요시 금융 상품 추천 정보를 제공합니다.
    """
    try:
        # 속도 제한 체크
        # rate_limit(request)  # 실제 서비스에서 필요시 주석 해제
        
        # 메시지 분석 - 주제와 감정 모두 분석
        analysis_start = time.time()
        message_analysis = analyze_message(req.message)
        is_finance = message_analysis.get("is_finance", False)
        emotion_data = message_analysis.get("emotion", {})
        logger.debug(f"메시지 분석 소요 시간: {time.time() - analysis_start:.2f}초")
        
        # 감정 분석 결과를 응답 모델로 변환
        emotion_result = None
        if emotion_data and "dominant_emotion" in emotion_data:
            emotion_result = EmotionResult(
                dominant_emotion=emotion_data.get("dominant_emotion", "중립"),
                dominant_score=emotion_data.get("dominant_score", 0.0),
                is_negative=emotion_data.get("is_negative", False),
                is_anxious=emotion_data.get("is_anxious", False),
                all_emotions=emotion_data.get("all_emotions", {})
            )
        
        # 금융 관련 질문인 경우
        if is_finance:
            reply, scen = await get_finance_reply(req.user_id, req.message)
            
            # 상품 추천 정보 추출
            clean_reply, product_recommendation = extract_product_recommendation(reply)
            
            # 시나리오 정보가 있는 경우 모델에 맞게 변환
            scenario_result = None
            if scen:
                scenario_result = ScenarioResult(
                    label=scen["label"],
                    probability=scen["probability"],
                    key_metrics=scen["key_metrics"]
                )
            
            # 상품 추천 정보가 있는 경우 응답에 포함
            if product_recommendation:
                response = ChatResponse(
                    reply=clean_reply,
                    scenario=scenario_result,
                    emotion=emotion_result,
                    product_recommendation=product_recommendation
                )
            else:
                response = ChatResponse(
                    reply=reply,
                    scenario=scenario_result,
                    emotion=emotion_result
                )
        else:
            # 일반 대화인 경우
            reply = await get_generic_reply(req.user_id, req.message)
            response = ChatResponse(reply=reply, emotion=emotion_result)
        
        # 백그라운드 작업으로 로깅 및 감정 데이터 기록
        background_tasks.add_task(log_chat, req, response, is_finance, emotion_data)
        
        # 감정 데이터 기록 (백그라운드 작업으로 처리)
        if emotion_data:
            background_tasks.add_task(record_emotion, req.user_id, emotion_data)
        
        return response
        
    except Exception as e:
        logger.error(f"Chat error: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="내부 서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        )
