from fastapi import Depends, HTTPException, status, Request, Header
from typing import Optional
import time
import os
from app.core.config import get_settings

settings = get_settings()

def verify_api_key(x_api_key: str = Header(None)):
    """API 키 검증 (특정 엔드포인트에만 적용)
    
    중요 엔드포인트 호출 시 API 키 검증을 위한 의존성
    """
    api_key = os.getenv("API_KEY")
    
    # API 키가 설정되지 않은 개발 환경에서는 검증 건너뛰기
    if not api_key or settings.ENVIRONMENT == "development":
        return
    
    if not x_api_key or x_api_key != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )

def get_rate_limit(tier: str = "standard"):
    """속도 제한 설정 - 사용자 등급에 따라 차등 적용
    
    Args:
        tier: 사용자 등급 ("standard", "premium", "enterprise")
    """
    limits = {
        "standard": {"rate": 10, "per": 60},     # 10 req/min
        "premium": {"rate": 60, "per": 60},      # 60 req/min
        "enterprise": {"rate": 1000, "per": 60}, # 1000 req/min
    }
    
    return limits.get(tier, limits["standard"])

def rate_limiter(request: Request, tier: str = "standard"):
    """속도 제한 의존성
    
    - Redis로 구현하는 것이 더 좋습니다(특히 다중 인스턴스 환경에서)
    - 현재는 메모리 내 간단한 구현
    """
    # 개발 환경에서는 속도 제한 비활성화
    if settings.ENVIRONMENT == "development" and not settings.DEBUG:
        return
    
    # 현재 시간 및 IP 주소
    timestamp = time.time()
    client_ip = request.client.host
    
    # 사용자 ID가 있으면 그것을 사용, 없으면 IP 주소
    user_id = request.query_params.get("user_id", client_ip)
    
    # 요청 기록 키
    request_key = f"rate_limit:{user_id}"
    
    # 메모리에 저장된 이전 요청들
    if not hasattr(request.app.state, "rate_limit_store"):
        request.app.state.rate_limit_store = {}
    
    limit = get_rate_limit(tier)
    rate = limit["rate"]
    per = limit["per"]
    
    # 이전 요청 목록 가져오기
    requests = request.app.state.rate_limit_store.get(request_key, [])
    
    # 기간 내 요청만 필터링
    requests = [req_time for req_time in requests if timestamp - req_time < per]
    
    # 한도 초과 체크
    if len(requests) >= rate:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {rate} requests per {per} seconds"
        )
    
    # 현재 요청 추가
    requests.append(timestamp)
    request.app.state.rate_limit_store[request_key] = requests
