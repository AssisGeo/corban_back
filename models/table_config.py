from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime


class TableConfigItem(BaseModel):
    table_id: str
    name: str
    description: str
    active: bool
    bank_name: str
    updated_at: datetime = datetime.utcnow()
    updated_by: Optional[str] = None


class TableConfig(BaseModel):
    tables: Dict[str, TableConfigItem]
    last_updated: datetime = datetime.utcnow()
