from pydantic import BaseModel
from typing import List, Optional


class BankUpdateRequest(BaseModel):
    active: bool
    features: Optional[List[str]] = None
    updated_by: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "active": True,
                "features": ["simulation", "proposal"],
                "updated_by": "admin@example.com",
            }
        }


class BankAddRequest(BaseModel):
    bank_name: str
    description: str
    active: bool = False
    features: List[str] = []
    updated_by: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "bank_name": "NOVO_BANCO",
                "description": "Novo Banco de Crédito",
                "active": True,
                "features": ["simulation"],
                "updated_by": "admin@example.com",
            }
        }
