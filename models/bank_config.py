# models/bank_config.py
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime


class BankConfigItem(BaseModel):
    bank_name: str
    active: bool
    features: List[str]
    description: str
    updated_at: datetime = datetime.utcnow()
    updated_by: Optional[str] = None


class BankConfig(BaseModel):
    banks: Dict[str, BankConfigItem]
    last_updated: datetime = datetime.utcnow()
