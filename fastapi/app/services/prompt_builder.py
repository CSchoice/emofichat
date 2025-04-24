def build_finance_advice(scen):
    if scen.label == "low_cash":
        return (f"현재 유동성이 부족해 보입니다(L={scen.key_metrics['Liquidity']}). "
                "다음 달 카드 사용을 30% 줄여보세요!")
    return "재무 상태가 양호해 보이네요 👍"
