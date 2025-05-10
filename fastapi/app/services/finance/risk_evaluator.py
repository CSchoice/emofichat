"""
재무 리스크 평가기

사용자의 재무 상태를 바탕으로 리스크를 평가하고 경고를 생성합니다.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

from app.services.finance.analyzer import get_finance_analyzer

# 로거 설정
logger = logging.getLogger(__name__)

class FinanceRiskEvaluator:
    """재무 리스크 평가 클래스"""
    
    def __init__(self, thresholds=None):
        self.finance_analyzer = get_finance_analyzer(thresholds)
        self.thresholds = thresholds or self.finance_analyzer.thresholds
        
    def evaluate_risk(self, row: Dict[str, Any], emotion_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        사용자의 재무 리스크 평가
        
        Args:
            row: 사용자 재무 데이터
            emotion_data: 감정 분석 결과 (선택적)
            
        Returns:
            리스크 평가 결과
        """
        try:
            # 기본 결과 구조
            result = {
                "risk_score": 50,       # 0-100 점수
                "risk_level": "중간",    # 높음, 중간, 낮음
                "risk_factors": [],      # 위험 요소 목록
                "warning_needed": False, # 경고 필요 여부
                "warning_level": "정보", # 정보, 주의, 경고, 심각
                "action_items": []       # 권장 조치 목록
            }
            
            # 데이터가 없는 경우
            if not row:
                return result
                
            # 재무 추세 분석
            trends = self.finance_analyzer.analyze_financial_trends(row)
            
            # 재무 건전성 평가
            health = self.finance_analyzer.evaluate_financial_health(row)
            
            # 리스크 점수 계산 (건전성 점수의 역수)
            risk_score = 100 - health.get("health_score", 50)
            result["risk_score"] = risk_score
            
            # 리스크 수준 결정
            if risk_score >= 70:
                result["risk_level"] = "높음"
            elif risk_score >= 30:
                result["risk_level"] = "중간"
            else:
                result["risk_level"] = "낮음"
            
            # 위험 요소 추가
            result["risk_factors"] = health.get("key_issues", [])
            
            # 감정 데이터가 있는 경우 감정 요소 추가
            if emotion_data:
                is_negative = emotion_data.get("is_negative", False)
                is_anxious = emotion_data.get("is_anxious", False)
                dominant_emotion = emotion_data.get("dominant_emotion", "중립")
                
                # 부정적 감정이 있는 경우 리스크 점수 증가
                if is_negative:
                    risk_score += 10
                    result["risk_factors"].append("부정적 감정 상태")
                
                # 불안 감정이 있는 경우 리스크 점수 증가
                if is_anxious:
                    risk_score += 15
                    result["risk_factors"].append("불안 감정 상태")
                
                # 리스크 점수 범위 조정
                risk_score = max(0, min(100, risk_score))
                result["risk_score"] = risk_score
                
                # 감정 상태에 따른 리스크 수준 재조정
                if is_negative and is_anxious and risk_score >= 60:
                    result["risk_level"] = "높음"
            
            # 경고 필요 여부 결정
            warning_needed = False
            warning_level = "정보"
            
            # 연체 여부
            if "is_delinquent" in row and row["is_delinquent"]:
                warning_needed = True
                warning_level = "심각"
                result["action_items"].append("연체 상환 계획 수립")
            
            # 스트레스 지수
            stress_index = trends.get("stress_index", 0)
            if stress_index >= self.thresholds["STRESS_HIGH"]:
                warning_needed = True
                warning_level = max(warning_level, "경고")
                result["action_items"].append("재무 스트레스 관리 방안 검토")
            
            # 유동성 점수
            liquidity_score = trends.get("liquidity_score", 50)
            if liquidity_score <= self.thresholds["LIQ_P20"]:
                warning_needed = True
                warning_level = max(warning_level, "주의")
                result["action_items"].append("유동성 확보 방안 검토")
            
            # 리스크 점수
            if risk_score >= 70:
                warning_needed = True
                warning_level = max(warning_level, "경고")
                result["action_items"].append("전반적인 재무 상황 점검")
            elif risk_score >= 50:
                warning_needed = True
                warning_level = max(warning_level, "주의")
            
            # 감정 상태
            if emotion_data:
                is_negative = emotion_data.get("is_negative", False)
                is_anxious = emotion_data.get("is_anxious", False)
                
                if is_negative and is_anxious:
                    warning_needed = True
                    warning_level = max(warning_level, "주의")
                    result["action_items"].append("감정 상태와 재무 스트레스 관리")
            
            # 경고 정보 설정
            result["warning_needed"] = warning_needed
            result["warning_level"] = warning_level
            
            # 기본 조치 항목 추가
            if not result["action_items"]:
                if risk_score >= 70:
                    result["action_items"] = [
                        "지출 계획 재검토",
                        "필수 지출 외 지출 줄이기",
                        "재무 상담 고려"
                    ]
                elif risk_score >= 50:
                    result["action_items"] = [
                        "예산 계획 수립",
                        "지출 모니터링 강화"
                    ]
                else:
                    result["action_items"] = [
                        "정기적인 재무 상태 점검"
                    ]
            
            return result
            
        except Exception as e:
            logger.error(f"재무 리스크 평가 중 오류 발생: {str(e)}")
            return {
                "risk_score": 50,
                "risk_level": "평가 실패",
                "risk_factors": ["데이터 분석 오류"],
                "warning_needed": False,
                "warning_level": "정보",
                "action_items": ["재무 상태 직접 확인"]
            }
    
    def generate_warning_message(self, risk_result: Dict[str, Any]) -> str:
        """
        리스크 평가 결과를 바탕으로 경고 메시지 생성
        
        Args:
            risk_result: 리스크 평가 결과
            
        Returns:
            경고 메시지
        """
        # 경고가 필요하지 않은 경우
        if not risk_result.get("warning_needed", False):
            return ""
            
        # 경고 수준
        warning_level = risk_result.get("warning_level", "정보")
        
        # 위험 요소
        risk_factors = risk_result.get("risk_factors", [])
        risk_factors_text = "\n".join([f"- {factor}" for factor in risk_factors]) if risk_factors else "- 특별한 위험 요소가 감지되지 않았습니다."
        
        # 권장 조치
        action_items = risk_result.get("action_items", [])
        action_items_text = "\n".join([f"- {item}" for item in action_items]) if action_items else "- 특별한 조치가 필요하지 않습니다."
        
        # 경고 메시지 템플릿
        templates = {
            "심각": (
                "⚠️ **재무 위험 경고** ⚠️\n\n"
                "현재 귀하의 재무 상태가 매우 심각한 수준입니다. 즉각적인 조치가 필요합니다.\n\n"
                "**위험 요소:**\n{risk_factors}\n\n"
                "**권장 조치:**\n{action_items}\n\n"
                "가능한 빨리 재무 상담을 받아보시기를 강력히 권장합니다."
            ),
            "경고": (
                "⚠️ **재무 주의 경고** ⚠️\n\n"
                "현재 귀하의 재무 상태에 주의가 필요합니다. 적절한 조치를 취하시기 바랍니다.\n\n"
                "**위험 요소:**\n{risk_factors}\n\n"
                "**권장 조치:**\n{action_items}\n\n"
                "상황이 악화되기 전에 재무 계획을 재검토하시기 바랍니다."
            ),
            "주의": (
                "🔔 **재무 주의 안내** 🔔\n\n"
                "귀하의 재무 상태에 약간의 주의가 필요합니다.\n\n"
                "**주의 요소:**\n{risk_factors}\n\n"
                "**권장 조치:**\n{action_items}\n\n"
                "재무 상황을 정기적으로 모니터링하시기 바랍니다."
            ),
            "정보": (
                "ℹ️ **재무 정보 안내** ℹ️\n\n"
                "귀하의 재무 상태에 대한 정보입니다.\n\n"
                "**참고 사항:**\n{risk_factors}\n\n"
                "**권장 사항:**\n{action_items}\n\n"
                "건전한 재무 관리를 위해 참고하시기 바랍니다."
            )
        }
        
        # 해당 경고 수준의 템플릿 선택
        template = templates.get(warning_level, templates["정보"])
        
        # 템플릿에 데이터 적용
        message = template.format(
            risk_factors=risk_factors_text,
            action_items=action_items_text
        )
        
        return message

# 싱글톤 인스턴스
_risk_evaluator = None

def get_risk_evaluator(thresholds=None) -> FinanceRiskEvaluator:
    """재무 리스크 평가기 싱글톤 인스턴스 반환"""
    global _risk_evaluator
    if _risk_evaluator is None:
        _risk_evaluator = FinanceRiskEvaluator(thresholds)
    return _risk_evaluator
