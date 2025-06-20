import math, re
from decimal import Decimal

_TH = re.compile(r"\{([A-Z_]+)\}")
_OP = {"&": " and ", "|": " or "}

# 한글 필드명 -> 영어 필드명 매핑
_FIELD_MAPPING = {
    # User 테이블
    "발급회원번호": "user_id",
    "남녀구분코드": "gender",
    "연령": "age",
    "거주시도명": "residence",
    "직장시도명": "workplace",
    "마케팅동의여부": "marketing_agree",
    
    # CardUsage 테이블
    "이용카드수_신용": "credit_card_count",
    "이용카드수_체크": "check_card_count",
    "이용금액_R3M_신용": "credit_usage_3m",
    "이용금액_R3M_체크": "check_usage_3m",
    "_1순위카드이용금액": "top1_card_usage",
    "_2순위카드이용금액": "top2_card_usage",
    "최초한도금액": "first_limit_amount",
    "카드이용한도금액": "current_limit_amount",
    "CA한도금액": "ca_limit_amount",
    
    # Delinquency 테이블
    "연체잔액_B0M": "delinquent_balance_b0m",
    "연체잔액_CA_B0M": "delinquent_balance_ca_b0m",
    "연체일수_최근": "recent_delinquent_days",
    "최종연체개월수_R15M": "max_delinquent_months_r15m",
    "회원여부_연체": "is_delinquent",
    "자발한도감액금액_R12M": "limit_down_amount_r12m",
    "한도증액금액_R12M": "limit_up_amount_r12m",
    "상향가능한도금액": "limit_up_available",
    
    # BalanceInfo 테이블
    "잔액_B0M": "balance_b0m",
    "잔액_일시불_B0M": "balance_lump_b0m",
    "잔액_카드론_B0M": "balance_loan_b0m",
    "평잔_3M": "avg_balance_3m",
    "평잔_CA_3M": "avg_ca_balance_3m",
    "평잔_카드론_3M": "avg_loan_balance_3m",
    "CA이자율_할인전": "ca_interest_rate",
    "RV최소결제비율": "revolving_min_payment_ratio",
    
    # SpendingPattern 테이블
    "이용금액_쇼핑": "spending_shopping",
    "이용금액_요식": "spending_food",
    "이용금액_교통": "spending_transport",
    "이용금액_의료": "spending_medical",
    "이용금액_납부": "spending_payment",
    "Life_Stage": "life_stage",
    "카드신청건수": "card_application_count",
    "최종카드발급경과월": "last_card_issued_months_ago",
    
    # ScenarioLabel 테이블
    "scenario_labels": "scenario_labels",
    "DTI_Estimate": "dti_estimate",
    "Spending_Change_Ratio": "spending_change_ratio",
    "Essential_Ratio": "essential_ratio",
    "Credit_Usage_Ratio": "credit_usage_ratio",
    "Debt_Ratio": "debt_ratio",
    "Revolving_Dependency": "revolving_dependency",
    "Necessity_Ratio": "necessity_ratio",
    "Housing_Ratio": "housing_ratio",
    "Medical_Ratio": "medical_ratio",
    
    # 추가 계산 필드 / 가상 필드
    "RV_평균잔액_R3M": "avg_revolving_balance_3m",
    "RV잔액이월횟수_R3M": "revolving_count_3m",
    "Stress_Index": "stress_index",
    "연체일수_B1M": "delinquent_days_b1m",
    "연체원금_최근": "recent_delinquent_principal",
    "Liquidity_Score": "liquidity_score",
    "월별총승인금액": "monthly_approval_amount",
    "월별총승인건수": "monthly_approval_count",
    "이용금액_신용_B0M": "credit_usage_b0m",
    "납부_전체이용금액": "total_payment_amount",
    "쇼핑_온라인_이용금액": "online_shopping_amount",
    "쇼핑_전체_이용금액": "total_shopping_amount",
    "VIP등급코드": "vip_grade"
}

def eval_expr(expr: str, row: dict, th: dict) -> bool:
    try:
        # 0. row의 Decimal 값을 float로 변환
        temp_row = {}
        for k, v in row.items():
            if isinstance(v, Decimal):
                temp_row[k] = float(v)
            else:
                temp_row[k] = v
        
        # 1. 임계값 치환 - 기본값 추가
        # 기본 임계값 설정 - 누락된 임계값이 있는 경우
        default_thresholds = {
            "CREDIT_USAGE_P90": 90,
            "LIQ_P20": 30,
            "LIQ_P80": 70,
            "DEBT_P80": 80,
            "DEBT_P50": 50,
            "NEC_P80": 0.8,
            "NEC_P20": 0.2,
            "STRESS_HIGH": 70,
            "HOUSING_P70": 0.3,
            "MEDICAL_P80": 0.2,
            "REVOLVING_P70": 0.7
        }
        
        # th에 없는 키를 default_thresholds에서 추가
        for key, value in default_thresholds.items():
            if key not in th:
                th[key] = value
                
        # 임계값을 문자열로 인식하는 경우도 처리 (credit_usage_ratio >= CREDIT_USAGE_P90 형태)
        if "CREDIT_USAGE_P90" in expr and "{CREDIT_USAGE_P90}" not in expr:
            expr = expr.replace("CREDIT_USAGE_P90", str(th.get("CREDIT_USAGE_P90", 90)))
        if "LIQ_P20" in expr and "{LIQ_P20}" not in expr:
            expr = expr.replace("LIQ_P20", str(th.get("LIQ_P20", 30)))
        if "LIQ_P80" in expr and "{LIQ_P80}" not in expr:
            expr = expr.replace("LIQ_P80", str(th.get("LIQ_P80", 70)))
        if "DEBT_P80" in expr and "{DEBT_P80}" not in expr:
            expr = expr.replace("DEBT_P80", str(th.get("DEBT_P80", 80)))
        
        expr = _TH.sub(lambda m: str(th.get(m.group(1), "math.nan")), expr)
        
        # 2. 연산자 변환
        for k, v in _OP.items():
            expr = expr.replace(k, v)
            
        # 3. 한글 필드명 -> 영어 필드명 변환
        for ko, en in _FIELD_MAPPING.items():
            if ko in expr:
                expr = expr.replace(ko, en)
                
        # 특별 처리: 필드가 없을 경우 기본값
        # eval 실행 전 필드들을 확인하고 없는 필드는 0이나 적절한 기본값으로 설정
        keys_in_expr = [key for key in _FIELD_MAPPING.values() if key in expr]
        for key in keys_in_expr:
            if key not in temp_row and key in expr:
                if "card_application_count" == key:
                    temp_row[key] = 0  # 카드신청건수가 없는 경우 0으로 가정
                elif any(key.startswith(prefix) for prefix in ["is_", "has_"]):
                    temp_row[key] = False  # 불리언 필드는 False로 기본값 설정
                else:
                    temp_row[key] = 0.0  # 숫자 필드는 0으로 기본값 설정
        
        # 4. 표현식 평가
        try:
            # 괄호로 감싸진 임계값이 있는 경우 처리
            # "credit_usage_ratio >= {CREDIT_USAGE_P90}" -> "credit_usage_ratio >= 90"
            bracket_thresholds = re.findall(r'\{([A-Z_0-9]+)\}', expr)
            for th_name in bracket_thresholds:
                if th_name in th:
                    expr = expr.replace(f"{{{th_name}}}", str(th[th_name]))
                else:
                    # 임계값이 없을 경우 default_thresholds에서 찾아보기
                    if th_name in default_thresholds:
                        expr = expr.replace(f"{{{th_name}}}", str(default_thresholds[th_name]))
                    else:
                        # 임계값을 찾을 수 없는 경우
                        print(f"임계값을 찾을 수 없음: {th_name}")
                        return False

            sandbox = {"__builtins__": {}, "math": math}
            result = bool(eval(expr, sandbox, temp_row))
            return result
        except Exception as e:
            print(f"표현식 평가 오류: {expr}")
            print(f"오류 메시지: {e}")
            return False
            
    except Exception as e:
        print(f"eval_expr 함수 오류: {expr}")
        print(f"오류 메시지: {e}")
        return False
