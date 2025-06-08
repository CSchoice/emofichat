# ── 기본값 ──────────────────────────────────────────────────
LIQ_P20, LIQ_P80         = 0.0000, 0.7953
DEBT_P80, DEBT_P50       = 1.2985, 0.7327
NEC_P80, NEC_P20         = 22.9239, 0.0000   # Essential_Ratio 기반
STRESS_HIGH              = 633367335.4003    # μ+σ (9723605.7637 + 623643729.6366)
HOUSING_P70              = 464460000.0000    # 활성 그룹 기준
MEDICAL_P80              = 0.3558
CREDIT_USAGE_P90         = 1.0404
REVOLVING_P70            = 0.3722            # 활성 그룹 기준

# dict 형태로도 노출 (eval_expr 에서 사용)
thresholds: dict[str, float] = globals()

# ── 동적 로더 ───────────────────────────────────────────────
def load_from_stats(stats: dict) -> None:
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
