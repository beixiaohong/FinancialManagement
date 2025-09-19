# app/models/sync_log.py
from sqlalchemy import (
    Column, Integer, String, DateTime,  ForeignKey
)
from sqlalchemy.sql import func
from .base import BaseModel

# --------------------
# 同步日志
# --------------------
class SyncLog(BaseModel):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    user_id = Column(Integer, ForeignKey("users.id"))

    table_name = Column(String(100))
    record_id = Column(Integer)
    operation = Column(String(50))  # INSERT, UPDATE, DELETE
    sync_timestamp = Column(DateTime(timezone=True), server_default=func.now())
