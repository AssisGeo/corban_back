from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class CardProposalResponse(BaseModel):
    proposal_number: str
    customer_id: str
    status: str
    success: bool
    error_message: Optional[str] = None
    formalization_link: Optional[str] = None


class CardListResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int
    pages: int
    has_next: bool
    has_prev: bool


class CardPipelineItem(BaseModel):
    customer_id: str
    customer_name: str
    cpf: str
    proposal_number: Optional[str] = None
    stage: str
    created_at: datetime
    updated_at: datetime
    status: str
    card_limit: Optional[float] = None
    has_proposal: bool
