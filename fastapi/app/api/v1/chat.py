from fastapi import APIRouter, HTTPException, Depends, status, Request, BackgroundTasks
from app.models import ChatRequest, ChatResponse, EmotionResult, ProductRecommendation, ScenarioResult
from app.services.topic_detector import is_finance_topic, analyze_emotion, analyze_message
from app.services.emotion_tracker import record_emotion
from app.services.generic_chat import get_generic_reply
from app.services.finance_chat import get_finance_reply
from app.services.product_recommender import PRODUCT_TYPE_DEPOSIT, PRODUCT_TYPE_FUND

# 금융 데이터베이스 서비스 추가
from app.services.database.user_financial_service import get_user_financial_service
from app.services.database.bank_product_service import get_bank_product_service
from app.services.database.fund_service import get_fund_service
from app.services.database.saving_product_service import get_saving_product_service

import logging
from typing import Optional, Dict, List, Any, Tuple
import time
import re
import json

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

def extract_product_recommendation(reply: str) -> Tuple[str, Optional[ProductRecommendation]]:
    """
    응답 텍스트에서 상품 추천 정보를 추출하고 텍스트와 구조화된 데이터로 분리합니다.
    
    Args:
        reply: 원본 응답 텍스트
        
    Returns:
        (기본 응답 텍스트, 추출된 상품 추천 정보)
    """
    # 상품 추천 섹션 판별 패턴
    recommendation_pattern = r'📌\s*\*\*(예금/적금|펀드)\s*상품\s*추천\*\*\s*\n\n([\s\S]*?)(?=해당\s*상품에\s*관심이|$)'
    
    # 상품 추천 섹션 검색
    match = re.search(recommendation_pattern, reply, re.DOTALL)
    if not match:
        logger.debug("상품 추천 섹션을 찾을 수 없습니다.")
        return reply, None
    
    # 상품 추천 섹션 추출
    product_type_text = match.group(1)
    product_section = match.group(0)
    
    logger.debug(f"발견된 상품 유형: {product_type_text}")
    logger.debug(f"추출된 상품 섹션: {product_section}")
    
    # 상품 유형 결정
    product_type = PRODUCT_TYPE_DEPOSIT if "예금" in product_type_text or "적금" in product_type_text else PRODUCT_TYPE_FUND
    
    # 원본 응답에서 상품 추천 섹션 제거
    clean_reply = reply.replace(product_section, "").strip()
    
    # 상품 목록 추출
    product_list = []
    
    if product_type == PRODUCT_TYPE_DEPOSIT:
        # 예금/적금 추천 패턴 - 좋은 방법은 여러 버전의 패턴을 시도하는 것
        # 패턴 1: 일반적인 포맷
        patterns = [
            # 패턴 1: 정규 포맷
            r'(\d+)\.\s*\*\*([^*]+)\*\*\s*\(([^)]+)\)\s*\n\s*-\s*상품유형:\s*([^\n]+)\s*\n\s*-\s*기본금리:\s*([^\n]+)(?:\s*\(최대\s*([^\n)]+)\))?\s*\n\s*-\s*계약기간:\s*([^\n]+)\s*\n\s*-\s*가입금액:\s*([^\n]+)',
            # 패턴 2: 유연성 있는 패턴 (개행수에 유의)
            r'(\d+)\.\s*\*\*([^*]+)\*\*\s*\(([^)]+)\)\s*\n\s*-\s*상품유형:\s*([^\n]+)\s*\n\s*-\s*기본금리:\s*([^\n]+)',
            # 패턴 3: 더 유연한 패턴 - 텍스트만 맞으면 상품으로 간주
            r'\*\*([^*]+)\*\*\s*\(([^)]+)\)'
        ]
        
        # 배열의 각 패턴을 순회하며 매칭 시도
        for pattern in patterns:
            for p_match in re.finditer(pattern, product_section, re.DOTALL):
                # 패턴별로 추출 로직이 다름
                if pattern == patterns[0]:  # 패턴 1: 정규 포맷
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
                elif pattern == patterns[1]:  # 패턴 2: 유연성 있는 패턴
                    product = {
                        "상품명": p_match.group(2).strip(),
                        "은행명": p_match.group(3).strip(),
                        "상품유형": p_match.group(4).strip(),
                        "기본금리": p_match.group(5).strip()
                    }
                else:  # 패턴 3: 최소 정보만 추출
                    product = {
                        "상품명": p_match.group(1).strip(),
                        "은행명": p_match.group(2).strip()
                    }
                
                # 이미 목록에 있는 상품인지 체크 (중복 상품 필터링)
                if not any(p.get("상품명") == product.get("상품명") for p in product_list):
                    product_list.append(product)
        
        # 상품이 출력되지 않을 경우 다른 방법 시도
        if not product_list:
            logger.debug("일반 패턴으로 상품을 추출할 수 없습니다. 모든 텍스트를 처리합니다.")
            # 추출 실패 시 빈 목록을 리턴하고 전체 텍스트를 사용
            return reply, None
    else:
        # 펀드 추천 패턴
        patterns = [
            # 패턴 1: 정규 포맷
            r'(\d+)\.\s*\*\*([^*]+)\*\*\s*\(([^)]+)\)\s*\n\s*-\s*유형:\s*([^\n]+)\s*\n\s*-\s*수익률:\s*([^\n]+)\s*\n\s*-\s*위험등급:\s*([^\n]+)',
            # 패턴 2: 최소 정보만 추출
            r'\*\*([^*]+)\*\*\s*\(([^)]+)\)'
        ]
        
        for pattern in patterns:
            for p_match in re.finditer(pattern, product_section, re.DOTALL):
                if pattern == patterns[0]:  # 패턴 1: 정규 포맷
                    product = {
                        "펀드명": p_match.group(2).strip(),
                        "운용사": p_match.group(3).strip(),
                        "유형": p_match.group(4).strip(),
                        "수익률": p_match.group(5).strip(),
                        "위험등급": p_match.group(6).strip()
                    }
                else:  # 패턴 2: 최소 정보만 추출
                    product = {
                        "펀드명": p_match.group(1).strip(),
                        "운용사": p_match.group(2).strip()
                    }
                
                # 이미 목록에 있는 상품인지 체크 (중복 상품 필터링)
                if not any(p.get("펀드명") == product.get("펀드명") for p in product_list):
                    product_list.append(product)
        
        # 상품이 출력되지 않을 경우 다른 방법 시도
        if not product_list:
            logger.debug("펀드 패턴으로 상품을 추출할 수 없습니다. 모든 텍스트를 처리합니다.")
            # 추출 실패 시 빈 목록을 리턴하고 전체 텍스트를 사용
            return reply, None
    
    # 추출한 상품이 없으면 None 반환
    if not product_list:
        logger.debug("추출된 상품이 없습니다.")
        return reply, None
    
    # 디버그 로그
    logger.info(f"상품 추출 결과: {len(product_list)}개 추출됨")
    
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
            # 사용자의 금융 정보 조회 시도
            financial_data = None
            try:
                user_financial_service = get_user_financial_service()
                financial_summary = await user_financial_service.get_user_financial_summary(req.user_id)
                
                if "error" not in financial_summary:
                    financial_data = financial_summary
                    logger.info(f"사용자 {req.user_id}의 금융 정보를 성공적으로 조회했습니다.")
                else:
                    logger.warning(f"사용자 {req.user_id}의 금융 정보 조회 실패: {financial_summary.get('error')}")
            except Exception as e:
                logger.error(f"금융 데이터베이스 조회 오류: {str(e)}")
            
            # 금융 챗봇 응답 생성
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
            
            # 상품 추천 키워드 확인 (정규식 일치 여부와 관계없이 체크)
            has_product_keywords = any(keyword in reply for keyword in ["**예금/적금 상품 추천**", "**펀드 상품 추천**", "기본금리", "위험등급", "은행명", "펀드명"])
            
            # 금융 데이터가 있고 특별한 키워드가 있는 경우 금융 데이터 조회
            financial_info = None
            if any(keyword in req.message.lower() for keyword in ["잔액", "계좌", "카드", "대출", "연체", "재무상태", "금융상태", "금융정보"]):
                try:
                    if financial_data:
                        # 금융 건강 정보 추가
                        financial_health = financial_data.get("financial_health", {})
                        financial_info = {
                            "balance": financial_data.get("balance", {}).get("balance", 0),
                            "loan_balance": financial_data.get("balance", {}).get("balance_loan", 0),
                            "is_delinquent": financial_data.get("delinquency", {}).get("is_delinquent") == "Y",
                            "health_score": financial_health.get("score", 50),
                            "health_grade": financial_health.get("grade", "보통")
                        }
                        logger.info(f"사용자 {req.user_id}의 금융 정보를 응답에 포함합니다.")
                except Exception as e:
                    logger.error(f"금융 정보 처리 오류: {str(e)}")
            
            # 상품 추천 정보가 있는 경우 응답에 포함
            if product_recommendation or has_product_keywords:
                # 정규식으로 추출된 상품이 있으면 그것을 사용하고, 없다면 reply 전체를 달아주기
                response = ChatResponse(
                    reply=reply,  # 클린 리플라이가 아니라 전체 리플라이를 활용
                    scenario=scenario_result,
                    emotion=emotion_result,
                    product_recommendation=product_recommendation,
                    financial_info=financial_info
                )
            else:
                response = ChatResponse(
                    reply=reply,
                    scenario=scenario_result,
                    emotion=emotion_result,
                    financial_info=financial_info
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
