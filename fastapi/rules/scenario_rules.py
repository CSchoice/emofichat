scenario_rules = {
    "loan_rejected": {
        "gate": [{"expr": "카드신청건수 > 0"}],
        "signals": [
            {"expr": "강제한도감액금액_R12M > 0", "weight": 2},
            {"expr": "Stress_Index >= {STRESS_HIGH}", "weight": 1},
            {"expr": "(연체일수_B1M > 0) | (연체잔액_B0M > 0)", "weight": 1}  # or → |
        ],
        "modifiers": [
            {"expr": "회원여부_연체 == 'Y'", "delta": 1},
            {"expr": "VIP등급코드 in ['Gold','Platinum','Black']", "delta": -1}
        ],
        "threshold": 3,
        "label": "loan_rejected"
    },

    "loan_approved": {
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
        "gate": [{"expr": "(연체일수_B1M > 0) | (연체잔액_B0M > 0)"}],  # or → |
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
        "gate": [{"expr": "(연체일수_B1M == 0) & (연체잔액_B0M == 0)"}],  # and → &
        "signals": [
            {"expr": "한도증액금액_R12M > 0", "weight": 2},
            {"expr": "상향가능한도금액 > 0", "weight": 1}
        ],
        "modifiers": [],
        "threshold": 2,
        "label": "credit_up"
    },

    "interest_burden": {
        "gate": [{"expr": "RV_평균잔액_R3M > 0"}],
        "signals": [
            {"expr": "RV잔액이월횟수_R3M >= 2", "weight": 2},
            {"expr": "Revolving_Dependency >= {REVOLVING_P70}", "weight": 1},
            {"expr": "CA이자율_할인전 > 15", "weight": 1}
        ],
        "modifiers": [
            {"expr": "잔액_카드론_B0M > 0", "delta": 1}  # 추가: 카드론 이용 중
        ],
        "threshold": 3,
        "label": "interest_burden"
    },

    "card_payment_difficulty": {
        "gate": [{"expr": "Credit_Usage_Ratio >= {CREDIT_USAGE_P90}"}],
        "signals": [
            {"expr": "RV잔액이월횟수_R3M >= 2", "weight": 1},
            {"expr": "(연체일수_B1M > 0) & (연체일수_B1M < 30)", "weight": 2},  # and → &
            {"expr": "잔액_B0M > 평잔_3M", "weight": 1}
        ],
        "modifiers": [
            {"expr": "Necessity_Ratio >= {NEC_P80}", "delta": 1}  # 추가: 필수지출 비율 높음
        ],
        "threshold": 3,
        "label": "card_payment_difficulty"
    },

    "delinquency": {
        "gate": [{"expr": "(연체일수_B1M >= 30) | (연체일수_최근 >= 30)"}],  # or → |
        "signals": [
            {"expr": "연체잔액_B0M > 0", "weight": 2},
            {"expr": "최종연체개월수_R15M > 0", "weight": 1}
        ],
        "modifiers": [{"expr": "연체원금_최근 > 500000", "delta": 1}],
        "threshold": 3,
        "label": "delinquency"
    },

    "low_cash": {
        "gate": [{"expr": "Liquidity_Score <= {LIQ_P20}"}],
        "signals": [
            {"expr": "Necessity_Ratio >= {NEC_P80}", "weight": 2},
            {"expr": "평잔_3M < 300000", "weight": 1},
            {"expr": "(이용금액_쇼핑 + 이용금액_요식 + 이용금액_납부) >= (월별총승인금액 * 0.6)", "weight": 1}  # 추가: 필수지출 비중
        ],
        "modifiers": [
            {"expr": "Life_Stage in ['1인가구', '대학생']", "delta": 1},  # 추가: 취약 Life_Stage
            {"expr": "VIP등급코드 in ['Gold','Platinum','Black']", "delta": -1}  # 추가: VIP 고객
        ],
        "threshold": 3,
        "label": "low_cash"
    },

    "debt_crisis": {
        "gate": [{"expr": "Debt_Ratio >= {DEBT_P80}"}],
        "signals": [
            {"expr": "(연체일수_B1M > 0) | (연체잔액_B0M > 0)", "weight": 2},  # or → |
            {"expr": "RV잔액이월횟수_R3M >= 3", "weight": 1},
            {"expr": "Credit_Usage_Ratio >= {CREDIT_USAGE_P90}", "weight": 1}  # 추가: 카드 한도 소진
        ],
        "modifiers": [
            {"expr": "잔액_B0M > 평잔_3M * 3", "delta": 1}
        ],
        "threshold": 3,
        "label": "debt_crisis"
    },

    "job_loss": {
        "gate": [{"expr": "월별총승인금액 < (이용금액_R3M_신용 * 0.5)"}],
        "signals": [
            {"expr": "(이용금액_R3M_신용 > 0) & (월별총승인금액 < 100000)", "weight": 2},  # and → &
            {"expr": "월별총승인건수 < 5", "weight": 1}
        ],
        "modifiers": [
            {"expr": "(연령 >= 35) & (연령 <= 55)", "delta": 1},  # and → &
            {"expr": "납부_전체이용금액 < (납부_전체이용금액 * 0.7)", "delta": 1}  # 추가: 고정비 감소
        ],
        "threshold": 2,
        "label": "job_loss"
    },

    "investment_loss": {
        "gate": [{"expr": "평잔_3M < (이용금액_R3M_신용 * 0.3)"}],
        "signals": [
            {"expr": "연체일수_B1M > 0", "weight": 1},
            {"expr": "Liquidity_Score <= {LIQ_P20}", "weight": 2},
            {"expr": "월별총승인금액 < (이용금액_R3M_신용 * 0.7)", "weight": 1}  # 추가: 지출 급감
        ],
        "modifiers": [
            {"expr": "VIP등급코드 in ['Gold','Platinum','Black']", "delta": 1}  # 추가: 투자 활동 고객층
        ],
        "threshold": 2,
        "label": "investment_loss"
    },

    "financial_hope": {
        "gate": [{"expr": "Liquidity_Score >= {LIQ_P80}"}],
        "signals": [
            {"expr": "상향가능한도금액 > 0", "weight": 1},
            {"expr": "(연체일수_B1M == 0) & (연체잔액_B0M == 0)", "weight": 1},  # and → &
            {"expr": "평잔_3M > 5000000", "weight": 1}  # 추가: 높은 평잔
        ],
        "modifiers": [
            {"expr": "VIP등급코드 in ['Gold','Platinum','Black']", "delta": 1},
            {"expr": "한도증액금액_R12M > 0", "delta": 1}  # 추가: 최근 한도증액
        ],
        "threshold": 2,
        "label": "financial_hope"
    },
    
    "recovering_debtor": {
        "gate": [{"expr": "(최종연체개월수_R15M > 0) & (연체일수_B1M == 0)"}],  # 과거 연체, 현재 정상
        "signals": [
            {"expr": "연체잔액_B0M == 0", "weight": 2},  # 현재 연체금 없음
            {"expr": "RV잔액이월횟수_R3M < 1", "weight": 1},  # 리볼빙 적게 사용
            {"expr": "Debt_Ratio < {DEBT_P50}", "weight": 1}  # 부채비율 낮아짐
        ],
        "modifiers": [
            {"expr": "한도증액금액_R12M > 0", "delta": 1}  # 최근 한도 증액
        ],
        "threshold": 2,
        "label": "recovering_debtor"
    },
    
    "emotional_spending": {
        "gate": [{"expr": "월별총승인건수 > 15"}],  # 잦은 결제
        "signals": [
            {"expr": "이용금액_쇼핑 > (이용금액_R3M_신용 * 0.5)", "weight": 2},  # 쇼핑 비중 높음
            {"expr": "쇼핑_온라인_이용금액 > (쇼핑_전체_이용금액 * 0.7)", "weight": 1},  # 온라인 쇼핑 비중
            {"expr": "이용금액_신용_B0M > (평잔_3M * 1.2)", "weight": 1}  # 수입보다 지출 많음
        ],
        "modifiers": [
            {"expr": "Necessity_Ratio < {NEC_P20}", "delta": 1}  # 필수지출 비율 낮음 (사치성 소비)
        ],
        "threshold": 3,
        "label": "emotional_spending"
    }
}