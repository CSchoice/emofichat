"""
간단한 룰 기반 시나리오 감지 예시
row(dict) + 사용자 발화 → (label, prob, 중요지표) 반환
"""

import re, math
from typing import Tuple, Dict, Any

# 키워드·임계값 예시
_LOWCASH_RE = re.compile(r"(카드값|결제|돈이 없어|잔액|💸)")
_STRESS_RE  = re.compile(r"(빚|연체|대출|한도|이자|한계)")

def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))

def score_scenarios(row: Dict[str, Any], user_msg: str) -> Tuple[str, float, Dict[str, float]]:
    """
    row = FinanceMetric dict, user_msg = 사용자 채팅
    """
    liq   = row.get("liquidity", 0)
    stress= row.get("stress", 0)
    debt  = row.get("debt_ratio", 0)

    # -------- Gate + Weight 샘플 -------- #
    if liq < 30 or _LOWCASH_RE.search(user_msg):
        prob = _sigmoid((30 - liq) / 10)            # 0~1
        return "low_cash", prob, {"liquidity": liq}

    if stress > 70 or _STRESS_RE.search(user_msg):
        prob = _sigmoid((stress - 70) / 10)
        return "debt_crisis", prob, {"stress": stress}

    if debt > 80:
        prob = _sigmoid((debt - 80) / 10)
        return "credit_down", prob, {"debt_ratio": debt}

    return "no_issue", 0.0, {}
