from pydantic import BaseModel, EmailStr, Field


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
    name: str = Field(default="")
    email: str = Field(default="")
    cpf: str = Field(default="")
    phone: str = Field(default="")
    zip_code: str = Field(default="")
    created_at: str
    status: str = Field(default="unknown")
    source: str = Field(default="unknown")

    model_config = {"from_attributes": True}
