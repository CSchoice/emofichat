import os, openai, backoff
from app.services.rule_engine import infer_scenario
from app.services.prompt_builder import build_finance_advice
from app.core.openai_client import client as openai_client

async def get_finance_reply(user_id: str, msg: str):
    scen = infer_scenario(user_id)
    advice = build_finance_advice(scen)

    resp = await openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "당신은 한국어 금융 컨설턴트 챗봇입니다."},
            {"role": "user", "content": msg},
            {"role": "assistant", "content": advice}
        ],
        temperature=0.7,
    )
    reply = resp.choices[0].message.content.strip()
    return reply, scen
