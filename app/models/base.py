from sqlalchemy import Column, Integer, DateTime, Boolean
from sqlalchemy.sql import func
from . import Base

class BaseModel(Base):
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True, comment="主键ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    is_deleted = Column(Boolean, default=False, comment="是否删除(软删除)")
