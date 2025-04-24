from fastapi import APIRouter
from app.models import ChatRequest, ChatResponse
from app.services.topic_detector import is_finance_topic
from app.services.generic_chat import get_generic_reply
from app.services.finance_chat import get_finance_reply

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if is_finance_topic(req.message):
        reply, scen = await get_finance_reply(req.user_id, req.message)
        return ChatResponse(reply=reply, scenario=scen)
    else:
        reply = await get_generic_reply(req.user_id, req.message)
        return ChatResponse(reply=reply)
