from pydantic import BaseModel
from typing import Optional


class MessageRequest(BaseModel):
    message: str


class SyncResponse(BaseModel):
    success: bool
    synced: Optional[int] = 0
    total_messages: Optional[int] = 0
    error: Optional[str] = None


class MessageResponse(BaseModel):
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
