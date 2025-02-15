from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class SessionCreate(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11)
    name: str = Field(..., min_length=3)
    email: EmailStr
    cpf: str = Field(..., min_length=11, max_length=11)
    zip_code: str = Field(..., min_length=8, max_length=8)

    model_config = {
        "json_schema_extra": {
            "example": {
                "phone": "11999999999",
                "name": "João Silva",
                "email": "joao@email.com",
                "cpf": "12345678900",
                "zip_code": "12345678",
            }
        }
    }


class SessionResponse(BaseModel):
    session_id: str
    name: Optional[str] = Field(default="")
    email: Optional[str] = Field(default="")
    cpf: Optional[str] = Field(default="")
    phone: Optional[str] = Field(default="")
    zip_code: Optional[str] = Field(default="")
    created_at: str
    status: Optional[str] = Field(default="unknown")
    source: Optional[str] = Field(default="unknown")

    model_config = {"from_attributes": True}
