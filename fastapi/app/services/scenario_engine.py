import math
from typing import Dict, Tuple, Any
from rules.scenario_rules import scenario_rules
from rules.thresholds import thresholds
from app.util.eval_expr import eval_expr

def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))

def score_scenarios(row: Dict[str, Any], user_msg: str = "") -> Tuple[str, float, Dict[str, float]]:
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
                signal_factors[s["expr"]] = row.get(s["expr"].split()[0], None)

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
