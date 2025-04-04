from pydantic import BaseModel, Field
from datetime import datetime


class InstallmentInfo(BaseModel):
    due_date: str
    amount: float


class NormalizedSimulationResponse(BaseModel):
    bank_name: str
    financial_id: str
    available_amount: float
    total_amount: float
    interest_rate: float
    iof_amount: float
    raw_response: dict
    timestamp: datetime = Field(default_factory=datetime.now)
