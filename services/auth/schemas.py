from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from .roles.constants import UserRole
from .roles.models import UserPermissions


class UserBase(BaseModel):
    email: EmailStr
    name: str


class UserCreate(UserBase):
    password: str
    role: UserRole = Field(default=UserRole.OPERATOR)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserPermissions


class UserResponse(UserBase):
    role: UserRole
    permissions: List[str] = []
    role_name: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str
