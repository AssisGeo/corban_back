from pydantic import BaseModel
from typing import List, Optional, Dict, Any
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


class ContractInfo(BaseModel):
    contract_number: str
    status: str
    has_contract: bool
    stage: str
    financial_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AddressInfo(BaseModel):
    zipCode: Optional[str] = None
    street: Optional[str] = None
    number: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class BankInfo(BaseModel):
    bankCode: Optional[str] = None
    bankName: Optional[str] = None
    accountType: Optional[str] = None
    accountNumber: Optional[str] = None
    accountDigit: Optional[str] = None
    branchNumber: Optional[str] = None


class CustomerInfo(BaseModel):
    name: str = ""
    cpf: str = ""
    phone_number: str
    email: Optional[str] = None
    address: Optional[Dict[str, Any]] = None
    bank_data: Optional[Dict[str, Any]] = None


class FinancialInfo(BaseModel):
    total_released: str = ""
    total_to_pay: str = ""
    interest_rate: str = ""
    iof_fee: str = ""
    installments: Optional[List[Dict[str, Any]]] = None


class FormalizationInfo(BaseModel):
    link: str = ""
    status: str
    sent_at: Optional[str] = None
    completed_at: Optional[str] = None


class EventInfo(BaseModel):
    type: str
    description: str
    timestamp: Optional[str] = None


class MetadataInfo(BaseModel):
    source: Optional[str] = None
    platform: Optional[str] = None
    send_by: Optional[str] = None
    origin: Optional[str] = None
    form_type: Optional[str] = None


class ContractDetailsResponse(BaseModel):
    contract: ContractInfo
    customer: CustomerInfo
    financial: FinancialInfo
    formalization: FormalizationInfo
    events: List[EventInfo] = []
    metadata: Optional[MetadataInfo] = None

    model_config = {"extra": "ignore"}  # Permite campos extras na validação
