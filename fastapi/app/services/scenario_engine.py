import math
import sys
import os
from typing import Dict, Tuple, Any
from pathlib import Path

# rules 모듈 경로 문제 해결
# 현재 파일의 경로를 기준으로 fastapi로 올라가서 rules 모듈 찾기
fastapi_root = Path(__file__).parent.parent.parent  # app/services/ 에서 3단계 위로 올라감

# 시스템 경로에 rules 모듈이 있는 디렉토리 추가
if fastapi_root not in sys.path:
    sys.path.append(str(fastapi_root))

from rules.scenario_rules import scenario_rules
from rules.thresholds import thresholds
from app.util.eval_expr import eval_expr

def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))

def score_scenarios(row: Dict[str, Any], user_msg: str = "") -> Tuple[str, float, Dict[str, str]]:
    """
    row(dict): 고객 1명의 금융 지표 및 분석값
    user_msg(str): 사용자의 발화 텍스트 (선택)

    return: (시나리오 라벨, 확률(0~1), 주요 관련 지표)
    """
    best_scenario = "neutral"
    best_score = 0.0
    best_factors = {}

    for scenario, rule in scenario_rules.items():
        # 1. gate 조건 확인
        if not all(eval_expr(g["expr"], row, thresholds) for g in rule.get("gate", [])):
            continue

        # 2. signal 점수 합산
        total_weight = sum(s["weight"] for s in rule["signals"])
        signal_score = 0
        signal_factors = {}
        for s in rule["signals"]:
            if eval_expr(s["expr"], row, thresholds):
                signal_score += s["weight"]
                # 표현식을 키로 사용하고, 값을 반드시 문자열로 변환
                key = s["expr"]
                value = row.get(s["expr"].split()[0], "")
                # None 값이 있는 경우 공백 문자열로 치환
                if value is None:
                    value = ""
                # 숫자나 그 외 값의 경우 문자열로 변환
                signal_factors[key] = str(value)

        # 3. modifier 적용
        for m in rule.get("modifiers", []):
            if eval_expr(m["expr"], row, thresholds):
                signal_score += m.get("delta", 0)

        # 4. 정규화된 확률 계산
        prob = _sigmoid(signal_score / (total_weight + 1e-5))

        if signal_score >= rule["threshold"] and prob > best_score:
            best_score = prob
            best_scenario = rule["label"]
            best_factors = signal_factors

    return best_scenario, round(best_score, 3), best_factors
