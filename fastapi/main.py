# main.py
from fastapi import FastAPI, Request, status, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import chat            # ← 폴더 구조에 맞춰 변경!
from dotenv import load_dotenv, find_dotenv
import logging
import time
import os
from app.core.logger import setup_logger

# 환경변수 로드
load_dotenv(find_dotenv())

# 로깅 설정
setup_logger()
logger = logging.getLogger(__name__)

# FastAPI 앱 인스턴스
app = FastAPI(
    title="Emotion-based Finance Chatbot",
    description="감정 기반 금융 상담 챗봇 API",
    version="0.2.0",
    docs_url="/docs", 
    redoc_url="/redoc",
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 운영 환경에서는 특정 도메인만 허용하는 것이 좋습니다
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 미들웨어 - 전체 요청 로깅
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # 요청 처리
    response = await call_next(request)
    
    # 처리 시간 계산
    process_time = time.time() - start_time
    
    # 로깅
    logger.info(
        f"{request.method} {request.url.path} {response.status_code} "
        f"({process_time:.4f}s)"
    )
    
    return response

# 전역 예외 처리
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # 에러 로깅
    logger.error(f"Unhandled exception: {type(exc).__name__}: {str(exc)}")
    
    # 사용자에게 보여줄 에러 메시지
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        }
    )

# 라우터 등록
app.include_router(chat.router, prefix="/api")

# 기본 루트 엔드포인트
@app.get("/")
async def root():
    env_mode = os.getenv("ENVIRONMENT", "development")
    return {
        "message": "Welcome to the Emotion-based Finance Chatbot API",
        "version": "0.2.0",
        "status": "healthy",
        "environment": env_mode
    }

@app.get("/health")
async def health_check():
    """서비스 상태 확인 엔드포인트"""
    return {
        "status": "ok",
        "timestamp": time.time()
    }

# 애플리케이션 시작 로그
logger.info("감정 기반 금융 챗봇 API 서버 시작")

# 애플리케이션 시작 이벤트
@app.on_event("startup")
async def startup_event():
    logger.info("서버 초기화 완료")
    
    # 메모리 캐시 구조 확인 - 문자열로 저장된 데이터를 객체로 변환
    try:
        from app.core.redis_client import memory_cache
        import json
        
        for key, items in memory_cache.data.items():
            if key.startswith("hist:") and items:
                converted = []
                for item in items:
                    if isinstance(item, str):
                        try:
                            converted.append(json.loads(item))
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse history item: {item}")
                    else:
                        converted.append(item)
                        
                memory_cache.data[key] = converted
                logger.debug(f"Converted memory cache data for {key}: {len(converted)} items")
    except Exception as e:
        logger.error(f"Error migrating memory cache: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("서버 종료")

