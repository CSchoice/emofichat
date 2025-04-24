# app/models/__init__.py
from pydantic import BaseModel
from typing import Optional, Dict

class ChatRequest(BaseModel):
    user_id: str
    message: str

class ScenarioResult(BaseModel):
    label: str
    probability: float
    key_metrics: Dict[str, str]

class ChatResponse(BaseModel):
    reply: str
    scenario: Optional[ScenarioResult] = None