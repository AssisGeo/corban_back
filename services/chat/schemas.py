from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime


class Message(BaseModel):
    type: str
    content: str
    timestamp: datetime


class MessageResponse(BaseModel):
    sender: str
    content: str


class ChatResponse(BaseModel):
    session_id: str
    customer_name: Optional[str] = None
    messages: List[Dict[str, str]] = []
    last_updated: Optional[datetime] = None
    contract_number: str = ""


class MessageContent(BaseModel):
    sender: str
    content: str
    timestamp: Optional[datetime] = None


class ChatStatsResponse(BaseModel):
    total_sessions: int
    active_today: int
    success_rate: float
    avg_duration_minutes: float
    total_messages: int
    completed_proposals: int
