"""
금융 건강 모니터링 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request, BackgroundTasks
from app.models import EmotionTrendsResponse, FinancialHealthResponse
from app.services.emotion_tracker import analyze_emotion_trends, get_emotion_history, get_financial_health_summary
import logging
from typing import Optional, List, Dict, Any
import time

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/emotion-trends/{user_id}", response_model=EmotionTrendsResponse)
async def get_emotion_trends(user_id: str, days: int = 30):
    """
    사용자의 감정 트렌드를 분석하여 반환합니다.
    
    Args:
        user_id: 사용자 ID
        days: 분석할 기간 (일)
        
    Returns:
        EmotionTrendsResponse: 감정 트렌드 분석 결과
    """
    try:
        start_time = time.time()
        result = await analyze_emotion_trends(user_id, days)
        
        if result.get("status") == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "감정 트렌드 분석 중 오류가 발생했습니다.")
            )
        
        if result.get("status") == "no_data":
            # 데이터가 없는 경우 404 대신 빈 결과를 반환합니다
            logger.info(f"User {user_id}: 감정 데이터가 없습니다.")
            return EmotionTrendsResponse(
                user_id=user_id,
                days=days,
                most_frequent_emotion="중립",
                emotion_frequency={},
                avg_emotion_scores={},
                financial_stress_index=0,
                stress_trend="데이터 없음",
                recommendations=["감정 분석을 위한 대화 데이터가 충분하지 않습니다."]
            )
        
        # 성공적인 결과 반환
        logger.info(f"User {user_id}: 감정 트렌드 분석 완료 ({time.time() - start_time:.2f}초)")
        return EmotionTrendsResponse(
            user_id=user_id,
            days=days,
            most_frequent_emotion=result.get("most_frequent_emotion", "중립"),
            emotion_frequency=result.get("emotion_frequency", {}),
            avg_emotion_scores=result.get("avg_emotion_scores", {}),
            negative_ratio=result.get("negative_ratio", 0),
            anxious_ratio=result.get("anxious_ratio", 0),
            emotion_volatility=result.get("emotion_volatility", 0),
            financial_stress_index=result.get("financial_stress_index", 0),
            stress_trend=result.get("stress_trend", "변화 없음"),
            data_points=result.get("data_points", 0),
            recommendations=result.get("recommendations", [])
        )
    
    except HTTPException as e:
        # 이미 처리된 에러는 그대로 전달
        raise
    
    except Exception as e:
        logger.error(f"감정 트렌드 분석 중 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="감정 트렌드 분석 중 예상치 못한 오류가 발생했습니다."
        )

@router.get("/financial-health/{user_id}", response_model=FinancialHealthResponse)
async def get_financial_health(user_id: str):
    """
    사용자의 금융 건강 상태를 분석하여 반환합니다.
    감정 트렌드와 금융 데이터를 결합한 종합적인 분석 결과를 제공합니다.
    
    Args:
        user_id: 사용자 ID
        
    Returns:
        FinancialHealthResponse: 금융 건강 분석 결과
    """
    try:
        start_time = time.time()
        result = await get_financial_health_summary(user_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자 데이터를 찾을 수 없습니다."
            )
        
        logger.info(f"User {user_id}: 금융 건강 분석 완료 ({time.time() - start_time:.2f}초)")
        
        emotion_data = result.get("emotion_analysis", {})
        
        return FinancialHealthResponse(
            user_id=user_id,
            financial_stress_index=emotion_data.get("financial_stress_index", 0),
            stress_trend=emotion_data.get("stress_trend", "변화 없음"),
            most_frequent_emotion=emotion_data.get("most_frequent_emotion", "중립"),
            emotion_volatility=emotion_data.get("emotion_volatility", 0),
            negative_ratio=emotion_data.get("negative_ratio", 0),
            summary=result.get("summary", ""),
            recommendations=result.get("recommendations", []),
            generated_at=result.get("generated_at", "")
        )
    
    except HTTPException as e:
        # 이미 처리된 에러는 그대로 전달
        raise
    
    except Exception as e:
        logger.error(f"금융 건강 분석 중 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="금융 건강 분석 중 예상치 못한 오류가 발생했습니다."
        )
