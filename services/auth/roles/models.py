from pydantic import BaseModel
from typing import List
from .constants import UserRole


class RoleInfo(BaseModel):
    id: int
    name: str
    permissions: List[str]


class RoleUpdate(BaseModel):
    role: UserRole


class UserPermissions(BaseModel):
    role: UserRole
    permissions: List[str]
    role_name: str
