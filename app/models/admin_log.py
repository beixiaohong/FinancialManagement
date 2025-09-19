# app/models/admin_log.py
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel

class AdminLog(BaseModel):
    __tablename__ = "admin_logs"
    __table_args__ = {'comment': '管理员操作日志表'}
    
    id = Column(Integer, primary_key=True, index=True)

    # 操作信息
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="管理员ID")
    action = Column(String(100), nullable=False, comment="操作类型")
    target_type = Column(String(50), nullable=True, comment="操作目标类型")
    target_id = Column(Integer, nullable=True, comment="操作目标ID")
    
    # 详细信息
    description = Column(Text, nullable=True, comment="操作描述")
    old_data = Column(JSON, nullable=True, comment="操作前数据")
    new_data = Column(JSON, nullable=True, comment="操作后数据")
    
    # 请求信息
    ip_address = Column(String(45), nullable=True, comment="IP地址")
    user_agent = Column(Text, nullable=True, comment="用户代理")
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


    # 关联关系
    admin = relationship("User")