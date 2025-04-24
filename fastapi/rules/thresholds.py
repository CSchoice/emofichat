"""
thresholds.py
  · 기본값을 먼저 정의해 두고
  · load_from_stats(stats: dict) 가 들어오면 실시간으로 덮어쓴다.
"""

# ── 기본값 ──────────────────────────────────────────────────
LIQ_P20, LIQ_P80         = 30, 70
DEBT_P80, DEBT_P50       = 80, 50
NEC_P80, NEC_P20         = 0.8, 0.2
STRESS_HIGH              = 70
HOUSING_P70              = 0.3
MEDICAL_P80              = 0.2
CREDIT_USAGE_P90         = 90
REVOLVING_P70            = 0.7

# dict 형태로도 노출 (eval_expr 에서 사용)
thresholds: dict[str, float] = globals()


# ── 동적 로더 ───────────────────────────────────────────────
def load_from_stats(stats: dict) -> None:
    """
    stats: 집계 결과 {지표명_quantile or _mu/_sigma: List/float}
    → thresholds 딕셔너리를 in-place 로 갱신
    """
    if "liquidity_score_q" in stats:
        thresholds["LIQ_P20"] = stats["liquidity_score_q"][1]
        thresholds["LIQ_P80"] = stats["liquidity_score_q"][5]

    if "debt_ratio_q" in stats:
        thresholds["DEBT_P80"] = stats["debt_ratio_q"][5]
        thresholds["DEBT_P50"] = stats["debt_ratio_q"][2]

    if "necessity_ratio_q" in stats:
        thresholds["NEC_P80"] = stats["necessity_ratio_q"][5]
        thresholds["NEC_P20"] = stats["necessity_ratio_q"][0]

    if {"stress_index_mu", "stress_index_sigma"} <= stats.keys():
        thresholds["STRESS_HIGH"] = (
            stats["stress_index_mu"] + stats["stress_index_sigma"]
        )

    if "housing_ratio_q" in stats:
        thresholds["HOUSING_P70"] = stats["housing_ratio_q"][4]

    if "medical_ratio_q" in stats:
        thresholds["MEDICAL_P80"] = stats["medical_ratio_q"][5]

    if "credit_usage_ratio_q" in stats:
        thresholds["CREDIT_USAGE_P90"] = stats["credit_usage_ratio_q"][6]

    if "revolving_dependency_q" in stats:
        thresholds["REVOLVING_P70"] = stats["revolving_dependency_q"][4]
