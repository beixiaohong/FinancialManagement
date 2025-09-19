# app/models/device.py
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey
)
from sqlalchemy.sql import func
from .base import BaseModel

# --------------------
# 设备表
# --------------------
class Device(BaseModel):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    device_name = Column(String(100))
    last_sync_at = Column(DateTime(timezone=True))