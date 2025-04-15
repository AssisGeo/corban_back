from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CredentialRequest(BaseModel):
    """Modelo para requisição de definição/atualização de credencial"""

    key: str
    value: str
    api_name: str
    description: Optional[str] = None
    updated_by: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "key": "FACTA_USER",
                "value": "usuario_api",
                "api_name": "FACTA",
                "description": "Usuário para API da Facta",
                "updated_by": "admin@example.com",
            }
        }


class CredentialResponse(BaseModel):
    """Modelo para resposta de listagem de credenciais"""

    key: str
    value: str
    api_name: str
    description: Optional[str] = None
    active: bool
    updated_at: datetime
    created_at: Optional[datetime] = None
    updated_by: Optional[str] = None
