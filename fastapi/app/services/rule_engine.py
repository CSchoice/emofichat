from random import random
from app.models import ScenarioResult

def dummy_metrics() -> tuple[float, float]:
    # Liquidity, Stress 임의 생성
    return round(random(),2), round(random(),2)

def infer_scenario(user_id: str) -> ScenarioResult:
    liq, stress = dummy_metrics()
    score = round((1-liq + stress)/2, 2)
    label = "low_cash" if score > 0.6 else "normal"
    return ScenarioResult(
        label=label,
        probability=score,
        key_metrics={"Liquidity": f"{liq}", "Stress": f"{stress}"}
    )
