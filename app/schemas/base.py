# app/schemas/base.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class BaseSchema(BaseModel):
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20
    
    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        return self.page_size

class PaginationResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    data: list