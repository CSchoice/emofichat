from __future__ import annotations

import logging
from typing import Dict, Any

# 로거 설정
logger = logging.getLogger(__name__)

def analyze_financial_trends(row: dict) -> dict:
    """사용자 재무 데이터의 트렌드를 분석하고 요약하는 함수
    
    다양한 시점의 데이터를 비교하여 변화 트렌드를 파악합니다.
    """
    trends = {}
    
    try:
        # 1. 잔액 추세 분석
        if all(key in row for key in ["balance_b0m", "balance_b1m", "balance_b2m"]):
            # 최근 3개월 동안의 잔액 변화
            b0 = row["balance_b0m"]
            b1 = row["balance_b1m"]
            b2 = row["balance_b2m"]
            
            # 잔액 변화율 계산 (%)
            if b1 > 0:
                change_1m = ((b0 - b1) / b1) * 100
            else:
                change_1m = 0
                
            if b2 > 0:
                change_2m = ((b0 - b2) / b2) * 100
            else:
                change_2m = 0
            
            # 추세 파악 및 저장
            if change_1m > 5 and change_2m > 0:  # 지속적 잔액 증가
                trends["balance_trend"] = "지속 증가"
            elif change_1m < -5 and change_2m < 0:  # 지속적 잔액 감소
                trends["balance_trend"] = "지속 감소"
            elif abs(change_1m) < 3:  # 안정적
                trends["balance_trend"] = "안정적"
            else:
                trends["balance_trend"] = "변동성 있음"
        
        # 2. 카드 사용 패턴 분석
        if all(key in row for key in ["card_usage_b0m", "card_usage_b1m", "card_usage_b2m"]):
            # 최근 3개월 동안의 카드 사용량 변화
            c0 = row["card_usage_b0m"]
            c1 = row["card_usage_b1m"] 
            c2 = row["card_usage_b2m"]
            
            # 평균 계산
            avg = (c0 + c1 + c2) / 3
            
            # 추세 파악
            if c0 > c1 and c1 > c2 and c0 > avg * 1.1:  # 지속 증가 추세
                trends["card_trend"] = "증가 추세"
            elif c0 < c1 and c1 < c2 and c0 < avg * 0.9:  # 지속 감소 추세
                trends["card_trend"] = "감소 추세"
            elif abs(c0 - avg) < avg * 0.1:  # 안정적
                trends["card_trend"] = "안정적"
            else:
                trends["card_trend"] = "불규칙"
        
        # 3. 잔액 vs 카드 사용 관계 분석
        if all(key in row for key in ["balance_b0m", "card_usage_b0m", "avg_balance_3m", "avg_card_usage_3m"]):
            bal_ratio = row["balance_b0m"] / (row["avg_balance_3m"] + 0.001)
            card_ratio = row["card_usage_b0m"] / (row["avg_card_usage_3m"] + 0.001)
            
            # 현재 상황 해석
            if bal_ratio < 0.7 and card_ratio > 1.2:  # 잔액 낮고 지출 높음
                trends["financial_health"] = "주의 필요"
            elif bal_ratio > 1.2 and card_ratio < 0.8:  # 잔액 높고 지출 낮음
                trends["financial_health"] = "양호한 상태"
            elif bal_ratio > 1.0 and card_ratio > 1.0:  # 잔액과 지출 모두 증가
                trends["financial_health"] = "소득 증가 가능성"
            else:
                trends["financial_health"] = "일반적"

        # 4. 재무 스트레스 지수 계산
        try:
            # 유동성 점수
            liquidity_score = row.get("liquidity_score", 50.0)  
            
            # 연체 여부
            is_delinquent = row.get("is_delinquent", 0) == 1
            
            # 카드 사용 비율 (현재 사용액 / 평균 사용액)
            card_usage_ratio = row.get("card_usage_b0m", 0) / (row.get("avg_card_usage_3m", 1) + 0.001)
            
            # 재무 스트레스 지수 계산 (0-100)
            stress_index = 50.0  # 기본값
            
            # 유동성 점수가 낮을수록 스트레스 증가
            stress_index += (50 - liquidity_score) * 0.5
            
            # 연체가 있으면 스트레스 크게 증가
            if is_delinquent:
                stress_index += 25
                
            # 카드 사용 비율이 높으면 스트레스 증가
            if card_usage_ratio > 1.2:
                stress_index += 10
            elif card_usage_ratio < 0.8:
                stress_index -= 5
                
            # 최종 스트레스 지수 범위 조정
            stress_index = min(100, max(0, stress_index))
            trends["stress_index"] = round(stress_index, 1)
            
            # 스트레스 수준 해석
            if stress_index > 75:
                trends["stress_level"] = "매우 높음"
            elif stress_index > 60:
                trends["stress_level"] = "높음"
            elif stress_index > 40:
                trends["stress_level"] = "보통"
            elif stress_index > 25:
                trends["stress_level"] = "낮음"
            else:
                trends["stress_level"] = "매우 낮음"
                
        except Exception as e:
            logger.warning(f"재무 스트레스 지수 계산 중 오류: {str(e)}")
            trends["stress_level"] = "알 수 없음"
            
    except Exception as e:
        logger.warning(f"재무 트렌드 분석 중 오류: {str(e)}")
        
    return trends
