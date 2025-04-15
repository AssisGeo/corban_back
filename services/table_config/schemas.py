from pydantic import BaseModel
from typing import Optional


class TableAddRequest(BaseModel):
    table_id: str
    name: str
    description: str
    bank_name: str
    active: bool = False
    updated_by: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "table_id": "58001",
                "name": "Tabela Promocional FACTA",
                "description": "Tabela com taxa reduzida",
                "bank_name": "FACTA",
                "active": True,
                "updated_by": "admin@example.com",
            }
        }
