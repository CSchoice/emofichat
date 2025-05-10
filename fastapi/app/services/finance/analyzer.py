"""
재무 상태 분석기

사용자의 재무 데이터를 분석하여 재무 상태를 평가합니다.
"""

import logging
from typing import Dict, Any, List, Optional
import statistics

# 로거 설정
logger = logging.getLogger(__name__)

class FinanceAnalyzer:
    """재무 상태 분석 클래스"""
    
    def __init__(self, thresholds=None):
        # 임계값 설정 (없으면 기본값 사용)
        self.thresholds = thresholds or {
            "CREDIT_USAGE_P90": 90,  # 신용 사용률 90% 이상은 위험
            "LIQ_P20": 30,           # 유동성 점수 30% 이하는 위험
            "LIQ_P80": 70,           # 유동성 점수 70% 이상은 안전
            "DEBT_P80": 80,          # 부채 비율 80% 이상은 위험
            "DEBT_P50": 50,          # 부채 비율 50% 이하는 안전
            "NEC_P80": 0.8,          # 필수 지출 비율 80% 이상은 위험
            "NEC_P20": 0.2,          # 필수 지출 비율 20% 이하는 안전
            "STRESS_HIGH": 70,       # 스트레스 지수 70 이상은 위험
            "HOUSING_P70": 0.3,      # 주거비 비율 30% 이상은 위험
            "MEDICAL_P80": 0.2,      # 의료비 비율 20% 이상은 위험
            "REVOLVING_P70": 0.7     # 리볼빙 비율 70% 이상은 위험
        }
        
    def analyze_financial_trends(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        사용자의 재무 데이터를 분석하여 추세 파악
        
        Args:
            row: 사용자 재무 데이터
            
        Returns:
            재무 추세 분석 결과
        """
        try:
            # 기본 결과 구조
            result = {
                "balance_trend": "안정적",
                "card_usage_trend": "안정적",
                "stress_index": 0,
                "liquidity_score": 50,
                "risk_factors": [],
                "positive_factors": []
            }
            
            # 데이터가 없는 경우
            if not row:
                return result
                
            # 잔액 추세 분석
            balances = []
            for i in range(6):
                bal_key = f"balance_b{i}m"
                if bal_key in row and row[bal_key] is not None:
                    balances.append(row[bal_key])
            
            # 잔액 데이터가 충분한 경우
            if len(balances) >= 3:
                # 최근 3개월 평균 대비 현재 잔액
                recent_avg = sum(balances[:3]) / 3
                if balances[0] > recent_avg * 1.2:
                    result["balance_trend"] = "지속 증가"
                    result["positive_factors"].append("잔액 증가 추세")
                elif balances[0] < recent_avg * 0.8:
                    result["balance_trend"] = "감소 추세"
                    result["risk_factors"].append("잔액 감소 추세")
                
                # 변동성 계산
                if len(balances) >= 3:
                    try:
                        variance = statistics.variance(balances[:3])
                        mean = statistics.mean(balances[:3])
                        if mean > 0:
                            cv = (variance ** 0.5) / mean  # 변동 계수
                            if cv > 0.3:
                                result["balance_trend"] = "불안정"
                                result["risk_factors"].append("잔액 변동성 높음")
                    except (statistics.StatisticsError, ZeroDivisionError):
                        pass
            
            # 카드 사용 추세 분석
            card_usages = []
            for i in range(6):
                usage_key = f"card_usage_b{i}m"
                if usage_key in row and row[usage_key] is not None:
                    card_usages.append(row[usage_key])
            
            # 카드 사용 데이터가 충분한 경우
            if len(card_usages) >= 3:
                # 최근 3개월 평균 대비 현재 사용액
                recent_avg = sum(card_usages[:3]) / 3
                if card_usages[0] > recent_avg * 1.2:
                    result["card_usage_trend"] = "증가 추세"
                    result["risk_factors"].append("카드 사용액 증가 추세")
                elif card_usages[0] < recent_avg * 0.8:
                    result["card_usage_trend"] = "감소 추세"
                    result["positive_factors"].append("카드 사용액 감소 추세")
            
            # 유동성 점수 계산
            liquidity_score = 50  # 기본값
            
            # 잔액 대비 카드 사용액 비율
            if "balance_b0m" in row and row["balance_b0m"] and "card_usage_b0m" in row and row["card_usage_b0m"]:
                if row["balance_b0m"] > 0:
                    usage_ratio = row["card_usage_b0m"] / row["balance_b0m"]
                    if usage_ratio > 1.0:
                        liquidity_score -= 20
                        result["risk_factors"].append("카드 사용액이 잔액을 초과")
                    elif usage_ratio < 0.3:
                        liquidity_score += 10
                        result["positive_factors"].append("카드 사용액이 잔액 대비 적절")
            
            # 연체 여부
            if "is_delinquent" in row and row["is_delinquent"]:
                liquidity_score -= 30
                result["risk_factors"].append("연체 상태")
            
            # 유동성 점수 범위 조정
            liquidity_score = max(0, min(100, liquidity_score))
            result["liquidity_score"] = liquidity_score
            
            # 스트레스 지수 계산
            stress_index = 0
            
            # 연체 여부에 따른 스트레스
            if "is_delinquent" in row and row["is_delinquent"]:
                stress_index += 50
            
            # 잔액 감소 추세에 따른 스트레스
            if "balance_trend" in result and result["balance_trend"] == "감소 추세":
                stress_index += 20
            
            # 카드 사용 증가 추세에 따른 스트레스
            if "card_usage_trend" in result and result["card_usage_trend"] == "증가 추세":
                stress_index += 15
            
            # 유동성 점수에 따른 스트레스
            if liquidity_score < self.thresholds["LIQ_P20"]:
                stress_index += 15
            
            # 스트레스 지수 범위 조정
            stress_index = max(0, min(100, stress_index))
            result["stress_index"] = stress_index
            
            # 위험 요소 추가
            if stress_index >= self.thresholds["STRESS_HIGH"]:
                result["risk_factors"].append("재무 스트레스 지수 높음")
            
            return result
            
        except Exception as e:
            logger.error(f"재무 추세 분석 중 오류 발생: {str(e)}")
            return {
                "balance_trend": "분석 실패",
                "card_usage_trend": "분석 실패",
                "stress_index": 0,
                "liquidity_score": 50,
                "risk_factors": ["데이터 분석 오류"],
                "positive_factors": []
            }
    
    def evaluate_financial_health(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        사용자의 재무 건전성 평가
        
        Args:
            row: 사용자 재무 데이터
            
        Returns:
            재무 건전성 평가 결과
        """
        try:
            # 기본 결과 구조
            result = {
                "health_score": 50,  # 0-100 점수
                "status": "보통",    # 위험, 주의, 보통, 양호, 우수
                "risk_level": "중간", # 높음, 중간, 낮음
                "key_issues": [],
                "strengths": []
            }
            
            # 데이터가 없는 경우
            if not row:
                return result
                
            # 재무 추세 분석
            trends = self.analyze_financial_trends(row)
            
            # 건전성 점수 계산
            health_score = 50  # 기본값
            
            # 유동성 점수 반영
            liquidity_score = trends.get("liquidity_score", 50)
            if liquidity_score >= self.thresholds["LIQ_P80"]:
                health_score += 15
                result["strengths"].append("높은 유동성")
            elif liquidity_score <= self.thresholds["LIQ_P20"]:
                health_score -= 15
                result["key_issues"].append("낮은 유동성")
            
            # 스트레스 지수 반영
            stress_index = trends.get("stress_index", 0)
            if stress_index >= self.thresholds["STRESS_HIGH"]:
                health_score -= 20
                result["key_issues"].append("높은 재무 스트레스")
            elif stress_index <= 30:
                health_score += 10
                result["strengths"].append("낮은 재무 스트레스")
            
            # 연체 여부 반영
            if "is_delinquent" in row and row["is_delinquent"]:
                health_score -= 30
                result["key_issues"].append("연체 상태")
            
            # 잔액 추세 반영
            if trends.get("balance_trend") == "지속 증가":
                health_score += 10
                result["strengths"].append("잔액 증가 추세")
            elif trends.get("balance_trend") == "감소 추세":
                health_score -= 10
                result["key_issues"].append("잔액 감소 추세")
            
            # 카드 사용 추세 반영
            if trends.get("card_usage_trend") == "증가 추세":
                health_score -= 5
                result["key_issues"].append("카드 사용액 증가 추세")
            elif trends.get("card_usage_trend") == "감소 추세":
                health_score += 5
                result["strengths"].append("카드 사용액 감소 추세")
            
            # 건전성 점수 범위 조정
            health_score = max(0, min(100, health_score))
            result["health_score"] = health_score
            
            # 상태 결정
            if health_score >= 80:
                result["status"] = "우수"
            elif health_score >= 65:
                result["status"] = "양호"
            elif health_score >= 40:
                result["status"] = "보통"
            elif health_score >= 20:
                result["status"] = "주의"
            else:
                result["status"] = "위험"
            
            # 위험 수준 결정
            if health_score >= 70:
                result["risk_level"] = "낮음"
            elif health_score >= 30:
                result["risk_level"] = "중간"
            else:
                result["risk_level"] = "높음"
            
            return result
            
        except Exception as e:
            logger.error(f"재무 건전성 평가 중 오류 발생: {str(e)}")
            return {
                "health_score": 50,
                "status": "평가 실패",
                "risk_level": "알 수 없음",
                "key_issues": ["데이터 분석 오류"],
                "strengths": []
            }

# 싱글톤 인스턴스
_finance_analyzer = None

def get_finance_analyzer(thresholds=None) -> FinanceAnalyzer:
    """재무 분석기 싱글톤 인스턴스 반환"""
    global _finance_analyzer
    if _finance_analyzer is None:
        _finance_analyzer = FinanceAnalyzer(thresholds)
    return _finance_analyzer

# 기존 코드와의 호환성을 위한 함수
def analyze_financial_trends(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    사용자의 재무 데이터를 분석하여 추세 파악 (호환성 함수)
    """
    analyzer = get_finance_analyzer()
    return analyzer.analyze_financial_trends(row)
