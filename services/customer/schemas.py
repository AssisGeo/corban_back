from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class CustomerBase(BaseModel):
    name: Optional[str] = Field(None, alias="NOME")
    cpf: Optional[str] = Field(None, alias="CPF")
    mother_name: Optional[str] = Field(None, alias="NOME_MAE")
    gender: Optional[str] = Field(None, alias="SEXO")
    birth_date: Optional[str] = Field(None, alias="NASC")
    address_number: Optional[str] = Field(None, alias="NUMERO")
    zip_code: Optional[str] = Field(None, alias="CEP")
    phone_ddd: Optional[str] = Field(None, alias="DDDCEL1")
    phone_number: Optional[str] = Field(None, alias="CEL1")
    email: Optional[str] = Field(None, alias="EMAIL1")


class CustomerUpdate(CustomerBase):
    pass


class CustomerListResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int
    pages: int


class CustomerUploadResponse(BaseModel):
    message: str
    total_processed: int
    success_count: int
    error_count: int


class CustomerStatsResponse(BaseModel):
    total_customers: int
    active_today: int
    success_rate: float
    avg_duration_minutes: float
    total_interactions: int
    completed_proposals: int
