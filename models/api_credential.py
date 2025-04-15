from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class APICredential(BaseModel):
    """Modelo para credencial de API"""

    key: str
    value: str
    api_name: str
    description: Optional[str] = None
    active: bool = True
    updated_at: datetime = datetime.utcnow()
    updated_by: Optional[str] = None
