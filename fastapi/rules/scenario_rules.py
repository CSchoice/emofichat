import json
from .thresholds import thresholds

# 원시 시나리오 룰셋 (플레이스홀더 포함, 우선순위(priority) 추가)
_raw_rules = {
    "loan_rejected": {
        "priority": 1,
        "gate": [{"expr": "카드신청건수 > 0"}],
        "signals": [
            {"expr": "강제한도감액금액_R12M > 0", "weight": 2},
            {"expr": "Stress_Index >= {STRESS_HIGH}", "weight": 1},
            {"expr": "(연체일수_B1M > 0) | (연체잔액_B0M > 0)", "weight": 1}
        ],
        "modifiers": [
            {"expr": "회원여부_연체 == 'Y'", "delta": 1},
            {"expr": "VIP등급코드 in ['Gold','Platinum','Black']", "delta": -1}
        ],
        "threshold": 3,
        "label": "loan_rejected"
    },
    "loan_approved": {
        "priority": 2,
        "gate": [{"expr": "카드신청건수 > 0"}],
        "signals": [
            {"expr": "한도증액금액_R12M > 0", "weight": 2},
            {"expr": "연체일수_B1M == 0", "weight": 1},
            {"expr": "Stress_Index < {STRESS_HIGH}", "weight": 1}
        ],
        "modifiers": [
            {"expr": "VIP등급코드 in ['Gold','Platinum','Black']", "delta": 1}
        ],
        "threshold": 3,
        "label": "loan_approved"
    },
    "credit_down": {
        "priority": 3,
        "gate": [{"expr": "(연체일수_B1M > 0) | (연체잔액_B0M > 0)"}],
        "signals": [
            {"expr": "Stress_Index >= {STRESS_HIGH}", "weight": 2},
            {"expr": "강제한도감액금액_R12M > 0", "weight": 1},
            {"expr": "최종연체개월수_R15M > 0", "weight": 1}
        ],
        "modifiers": [],
        "threshold": 3,
        "label": "credit_down"
    },
    "credit_up": {
        "priority": 4,
        "gate": [{"expr": "(연체일수_B1M == 0) & (연체잔액_B0M == 0)"}],
        "signals": [
            {"expr": "한도증액금액_R12M > 0", "weight": 2},
            {"expr": "상향가능한도금액 > 0", "weight": 1}
        ],
        "modifiers": [],
        "threshold": 2,
        "label": "credit_up"
    },
    "interest_burden": {
        "priority": 5,
        # 활성 사용자만 평가
        "gate": [
            {"expr": "RV_평균잔액_R3M > 0"},
            {"expr": "Revolving_Dependency > 0"}
        ],
        "signals": [
            {"expr": "RV잔액이월횟수_R3M >= 2", "weight": 2},
            {"expr": "Revolving_Dependency >= {REVOLVING_P70}", "weight": 1},
            {"expr": "CA이자율_할인전 > 15", "weight": 1}
        ],
        "modifiers": [
            {"expr": "잔액_카드론_B0M > 0", "delta": 1}
        ],
        "threshold": 3,
        "label": "interest_burden"
    },
    "card_payment_difficulty": {
        "priority": 6,
        "gate": [{"expr": "Credit_Usage_Ratio >= {CREDIT_USAGE_P90}"}],
        "signals": [
            {"expr": "RV잔액이월횟수_R3M >= 2", "weight": 1},
            {"expr": "(연체일수_B1M > 0) & (연체일수_B1M < 30)", "weight": 2},
            {"expr": "잔액_B0M > 평잔_3M", "weight": 1}
        ],
        "modifiers": [
            {"expr": "Necessity_Ratio >= {NEC_P80}", "delta": 1}
        ],
        "threshold": 3,
        "label": "card_payment_difficulty"
    },
    "delinquency": {
        "priority": 7,
        "gate": [{"expr": "(연체일수_B1M >= 30) | (연체일수_최근 >= 30)"}],
        "signals": [
            {"expr": "연체잔액_B0M > 0", "weight": 2},
            {"expr": "최종연체개월수_R15M > 0", "weight": 1}
        ],
        "modifiers": [{"expr": "연체원금_최근 > 500000", "delta": 1}],
        "threshold": 3,
        "label": "delinquency"
    },
    "low_cash": {
        "priority": 8,
        "gate": [{"expr": "Liquidity_Score <= {LIQ_P20}"}],
        "signals": [
            {"expr": "Necessity_Ratio >= {NEC_P80}", "weight": 2},
            {"expr": "평잔_3M < 300000", "weight": 1},
            {"expr": "(이용금액_쇼핑 + 이용금액_요식 + 이용금액_납부) >= (월별총승인금액 * 0.6)", "weight": 1}
        ],
        "modifiers": [
            {"expr": "Life_Stage in ['1인가구','대학생']", "delta": 1},
            {"expr": "VIP등급코드 in ['Gold','Platinum','Black']", "delta": -1}
        ],
        "threshold": 3,
        "label": "low_cash"
    },
    "debt_crisis": {
        "priority": 9,
        "gate": [{"expr": "Debt_Ratio >= {DEBT_P80}"}],
        "signals": [
            {"expr": "(연체일수_B1M > 0) | (연체잔액_B0M > 0)", "weight": 2},
            {"expr": "RV잔액이월횟수_R3M >= 3", "weight": 1},
            {"expr": "Credit_Usage_Ratio >= {CREDIT_USAGE_P90}", "weight": 1}
        ],
        "modifiers": [{"expr": "잔액_B0M > 평잔_3M * 3", "delta": 1}],
        "threshold": 3,
        "label": "debt_crisis"
    },
    "job_loss": {
        "priority": 10,
        "gate": [{"expr": "월별총승인금액 < (이용금액_R3M_신용 * 0.5)"}],
        "signals": [
            {"expr": "(이용금액_R3M_신용 > 0) & (월별총승인금액 < 100000)", "weight": 2},
            {"expr": "월별총승인건수 < 5", "weight": 1}
        ],
        "modifiers": [
            {"expr": "(연령 >= 35) & (연령 <= 55)", "delta": 1},
            {"expr": "납부_전체이용금액 < 납부_전체이용금액_전월 * 0.7", "delta": 1}
        ],
        "threshold": 2,
        "label": "job_loss"
    },
    "investment_loss": {
        "priority": 11,
        "gate": [{"expr": "평잔_3M < (이용금액_R3M_신용 * 0.3)"}],
        "signals": [
            {"expr": "연체일수_B1M > 0", "weight": 1},
            {"expr": "Liquidity_Score <= {LIQ_P20}", "weight": 2},
            {"expr": "월별총승인금액 < (이용금액_R3M_신용 * 0.7)", "weight": 1}
        ],
        "modifiers": [{"expr": "VIP등급코드 in ['Gold','Platinum','Black']", "delta": 1}],
        "threshold": 2,
        "label": "investment_loss"
    },
    "financial_hope": {
        "priority": 12,
        # 활성 그룹 기준 유동성 양호
        "gate": [
            {"expr": "Liquidity_Score > 0"},
            {"expr": "Liquidity_Score >= {LIQ_P80}"}
        ],
        "signals": [
            {"expr": "상향가능한도금액 > 0", "weight": 1},
            {"expr": "(연체일수_B1M == 0) & (연체잔액_B0M == 0)", "weight": 1},
            {"expr": "평잔_3M > 5000000", "weight": 1}
        ],
        "modifiers": [
            {"expr": "VIP등급코드 in ['Gold','Platinum','Black']", "delta": 1},
            {"expr": "한도증액금액_R12M > 0", "delta": 1}
        ],
        "threshold": 2,
        "label": "financial_hope"
    },
    "recovering_debtor": {
        "priority": 13,
        "gate": [{"expr": "(최종연체개월수_R15M > 0) & (연체일수_B1M == 0)"}],
        "signals": [
            {"expr": "연체잔액_B0M == 0", "weight": 2},
            {"expr": "RV잔액이월횟수_R3M < 1", "weight": 1},
            {"expr": "Debt_Ratio < {DEBT_P50}", "weight": 1}
        ],
        "modifiers": [{"expr": "한도증액금액_R12M > 0", "delta": 1}],
        "threshold": 2,
        "label": "recovering_debtor"
    },
    "emotional_spending": {
        "priority": 14,
        "gate": [{"expr": "월별총승인건수 > 15"}],
        "signals": [
            {"expr": "이용금액_쇼핑 > (이용금액_R3M_신용 * 0.5)", "weight": 2},
            {"expr": "쇼핑_온라인_이용금액 > (쇼핑_전체_이용금액 * 0.7)", "weight": 1},
            {"expr": "이용금액_신용_B0M > (평잔_3M * 1.2)", "weight": 1}
        ],
        "modifiers": [{"expr": "Necessity_Ratio < {NEC_P20}", "delta": 1}],
        "threshold": 3,
        "label": "emotional_spending"
    }
}


def bind_placeholders(rules: dict, params: dict) -> dict:
    for rule in rules.values():
        for section in ('gate', 'signals', 'modifiers'):
            for entry in rule.get(section, []):
                entry['expr'] = entry['expr'].format(**params)
    return rules

# thresholds 딕셔너리로부터 치환 후 룰셋 생성
scenario_rules = bind_placeholders(_raw_rules, thresholds)

# JSON 파일로 저장
with open('scenario_rules.json', 'w', encoding='utf-8') as f:
    json.dump(scenario_rules, f, ensure_ascii=False, indent=2)