"""
감정 데이터 API 엔드포인트

사용자의 감정 데이터를 조회하고 분석하는 API를 제공합니다.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request, BackgroundTasks
from typing import Dict, List, Any, Optional
import logging

from app.services.database.db_service import get_db_service
from app.models import EmotionTrendsResponse, FinancialHealthResponse

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/emotions/{user_id}", response_model=EmotionTrendsResponse)
async def get_emotion_trends(
    user_id: str,
    request: Request,
    days: int = 7
):
    """
    사용자의 감정 트렌드 데이터를 조회합니다.
    
    - **user_id**: 사용자 ID
    - **days**: 조회할 기간(일)
    """
    try:
        db_service = get_db_service()
        
        # 감정 트렌드 분석 결과 조회
        trend_data = await db_service.get_emotion_trend(user_id, days)
        
        if trend_data.get("data_points", 0) == 0:
            return EmotionTrendsResponse(
                user_id=user_id,
                days=days,
                most_frequent_emotion="중립",
                emotion_frequency={},
                avg_emotion_scores={},
                negative_ratio=0.0,
                anxious_ratio=0.0,
                emotion_volatility=0.0,
                financial_stress_index=0.0,
                stress_trend="stable",
                data_points=0,
                recommendations=["감정 데이터가 충분하지 않습니다. 더 많은 대화를 통해 감정 분석을 진행해보세요."]
            )
        
        # 응답 구성
        response = EmotionTrendsResponse(
            user_id=user_id,
            days=days,
            most_frequent_emotion=trend_data.get("most_frequent_emotion", "중립"),
            emotion_frequency=trend_data.get("emotion_frequency", {}),
            avg_emotion_scores=trend_data.get("avg_emotion_scores", {}),
            negative_ratio=trend_data.get("negative_ratio", 0.0),
            anxious_ratio=trend_data.get("anxious_ratio", 0.0),
            emotion_volatility=trend_data.get("emotion_volatility", 0.0),
            financial_stress_index=trend_data.get("financial_stress_index", 0.0),
            stress_trend=trend_data.get("stress_trend", "stable"),
            data_points=trend_data.get("data_points", 0),
            recommendations=trend_data.get("recommendations", [])
        )
        
        return response
        
    except Exception as e:
        logger.error(f"감정 트렌드 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="감정 트렌드 데이터를 조회하는 중 오류가 발생했습니다."
        )


@router.get("/financial-health/{user_id}", response_model=FinancialHealthResponse)
async def get_financial_health(
    user_id: str,
    request: Request
):
    """
    사용자의 재무 건강 상태를 조회합니다.
    
    - **user_id**: 사용자 ID
    """
    try:
        db_service = get_db_service()
        
        # 사용자 재무 프로필 조회
        profile = await db_service.get_or_create_financial_profile(user_id)
        
        # 감정 트렌드 분석 결과 조회
        trend_data = await db_service.get_emotion_trend(user_id, days=30)
        
        # 재무 건강 상태 계산
        financial_stress_index = 0.5  # 초기 기본값
        stress_trend = "stable"
        
        # 금융 데이터 조회 시도
        try:
            from app.services.database.user_financial_service import get_user_financial_service
            user_financial_service = get_user_financial_service()
            financial_summary = await user_financial_service.get_user_financial_summary(user_id)
            
            if "error" not in financial_summary:
                # 금융 건강 점수 가져오기
                financial_health = financial_summary.get("financial_health", {})
                health_score = financial_health.get("score", 50)
                
                # 부채 비율 가져오기
                scenario = financial_summary.get("scenario", {})
                debt_ratio = scenario.get("debt_ratio", 0.0)
                dti_estimate = scenario.get("dti_estimate", 0.0)
                
                # 연체 여부 가져오기
                delinquency = financial_summary.get("delinquency", {})
                is_delinquent = delinquency.get("is_delinquent") == "Y"
                
                # 금융 데이터 기반으로 스트레스 지수 계산
                # 건강 점수를 0~1 범위로 정규화 (100점 만점)
                health_factor = 1 - (health_score / 100.0)  # 점수가 낮을수록 스트레스 높음
                
                # 부채 비율 및 DTI 정규화 (0~1 범위)
                debt_factor = min(debt_ratio / 100.0, 1.0)  # 부채 비율이 높을수록 스트레스 높음
                dti_factor = min(dti_estimate / 1000000000.0, 1.0)  # DTI가 높을수록 스트레스 높음
                
                # 연체 여부 반영
                delinquent_factor = 1.0 if is_delinquent else 0.0
                
                # 가중치 적용하여 종합 스트레스 지수 계산
                financial_stress_index = (
                    health_factor * 0.4 +
                    debt_factor * 0.3 +
                    dti_factor * 0.2 +
                    delinquent_factor * 0.1
                )
                
                # 감정 데이터가 있는 경우 합산
                if trend_data.get("data_points", 0) > 0:
                    # 부정적 감정 비율과 불안 감정 비율을 기반으로 스트레스 지수 계산
                    negative_ratio = trend_data.get("negative_ratio", 0.0)
                    anxious_ratio = trend_data.get("anxious_ratio", 0.0)
                    emotion_volatility = trend_data.get("emotion_volatility", 0.0)
                    
                    # 감정 기반 스트레스 지수
                    emotion_stress_index = (negative_ratio * 0.4) + (anxious_ratio * 0.4) + (emotion_volatility * 0.2)
                    
                    # 금융 데이터와 감정 데이터를 합산하여 최종 스트레스 지수 계산
                    financial_stress_index = (financial_stress_index * 0.7) + (emotion_stress_index * 0.3)
        except Exception as e:
            logger.error(f"금융 데이터 기반 스트레스 지수 계산 오류: {str(e)}")
            # 오류 발생 시 기본값 유지
        
        # 스트레스 트렌드 결정
        if financial_stress_index > 0.7:
            stress_trend = "high"
        elif financial_stress_index > 0.4:
            stress_trend = "moderate"
        else:
            stress_trend = "low"
        
        # 맞춤형 추천 생성
        recommendations = []
        if financial_stress_index > 0.7:
            recommendations = [
                "재무 스트레스가 높습니다. 전문가와 상담을 고려해보세요.",
                "지출을 줄이고 필수 비용에 집중하는 것이 좋습니다.",
                "긴급 자금을 마련하는 것이 중요합니다."
            ]
        elif financial_stress_index > 0.4:
            recommendations = [
                "재무 계획을 세우고 지출을 관리하세요.",
                "저축 목표를 설정하고 정기적으로 저축하세요.",
                "불필요한 지출을 줄이는 것이 도움이 됩니다."
            ]
        else:
            recommendations = [
                "재무 상태가 양호합니다. 장기 투자를 고려해보세요.",
                "정기적인 재무 점검을 통해 상태를 유지하세요.",
                "미래를 위한 투자 포트폴리오를 다양화하세요."
            ]
        
        # 응답 구성
        response = FinancialHealthResponse(
            user_id=user_id,
            financial_stress_index=financial_stress_index,
            stress_trend=stress_trend,
            most_frequent_emotion=trend_data.get("most_frequent_emotion", "중립"),
            emotion_volatility=trend_data.get("emotion_volatility", 0.0),
            negative_ratio=trend_data.get("negative_ratio", 0.0),
            summary=f"재무 스트레스 지수는 {financial_stress_index:.2f}로 {stress_trend} 수준입니다.",
            recommendations=recommendations,
            generated_at=trend_data.get("generated_at", "")
        )
        
        return response
        
    except Exception as e:
        logger.error(f"재무 건강 상태 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="재무 건강 상태를 조회하는 중 오류가 발생했습니다."
        )
