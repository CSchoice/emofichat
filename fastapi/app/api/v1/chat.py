from fastapi import APIRouter, HTTPException, Depends, status, Request, BackgroundTasks
from app.models import ChatRequest, ChatResponse
from app.services.topic_detector import is_finance_topic
from app.services.generic_chat import get_generic_reply
from app.services.finance_chat import get_finance_reply
import logging
from typing import Optional
import time

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
async def log_chat(req: ChatRequest, response: ChatResponse, is_finance: bool):
    # 민감 정보 마스킹 - 실제 환경에서는 더 정교한 처리 필요
    masked_user_id = req.user_id[:3] + "****" if len(req.user_id) > 5 else "***"
    
    logger.info(
        f"Chat: user={masked_user_id}, type={'finance' if is_finance else 'general'}, "
        f"msg_len={len(req.message)}, reply_len={len(response.reply)}"
    )

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request, background_tasks: BackgroundTasks):
    """채팅 메시지 처리 엔드포인트
    
    금융 관련 메시지인지 판단하여 적절한 서비스로 라우팅합니다.
    """
    try:
        # 속도 제한 체크
        # rate_limit(request)  # 실제 서비스에서 필요시 주석 해제
        
        is_finance = is_finance_topic(req.message)
        
        if is_finance:
            reply, scen = await get_finance_reply(req.user_id, req.message)
            response = ChatResponse(reply=reply, scenario=scen)
        else:
            reply = await get_generic_reply(req.user_id, req.message)
            response = ChatResponse(reply=reply)
        
        # 백그라운드 작업으로 로깅
        background_tasks.add_task(log_chat, req, response, is_finance)
        
        return response
        
    except Exception as e:
        logger.error(f"Chat error: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="내부 서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        )
