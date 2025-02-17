from pydantic import BaseModel, Field, field_validator
from typing import Optional


class SessionCreate(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11)
    name: str = Field(..., min_length=3)
    email: Optional[str] = ""
    cpf: str = Field(..., min_length=11, max_length=11)
    zip_code: Optional[str] = ""

    @field_validator("phone", "cpf")
    @classmethod
    def validate_numeric_fields(cls, v):
        if v and not v.isdigit():
            raise ValueError("Must contain only digits")
        return v

    @field_validator("email")
    @classmethod
    def validate_optional_email(cls, v):
        return v if v else None

    model_config = {
        "json_schema_extra": {
            "example": {
                "phone": "11999999999",
                "name": "João Silva",
                "email": "",
                "cpf": "12345678900",
                "zip_code": "",
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
