# app/models/record.py
from sqlalchemy import Column, String, JSON, Integer, ForeignKey, Enum, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.types import DECIMAL
from .base import BaseModel
from sqlalchemy.sql import func
import enum

class RecordType(enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"

class Record(BaseModel):
    __tablename__ = "records"
    __table_args__ = {'comment': '记账记录表'}

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    
    record_type = Column(Enum(RecordType), nullable=False, comment="记录类型")
    amount = Column(DECIMAL(15, 2), nullable=False, comment="金额")
    record_date = Column(DateTime(timezone=True), nullable=False, comment="记录日期")
    description = Column(Text, nullable=True, comment="描述备注")
    
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, comment="账本ID")
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="创建者ID")
    payment_account_id = Column(Integer, ForeignKey("payment_accounts.id"), nullable=False, comment="支付账户ID")
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, comment="分类ID")
    
    target_payment_account_id = Column(Integer, ForeignKey("payment_accounts.id"), nullable=True, comment="目标账户ID")
    transfer_fee = Column(DECIMAL(10, 2), default=0, comment="手续费")

    type = Column(String(50))  # income / expense


    tags = Column(JSON, nullable=True, comment="标签（JSON格式）")
    location = Column(String(255), nullable=True, comment="消费地点")
    weather = Column(String(50), nullable=True, comment="天气情况")
    mood = Column(String(50), nullable=True, comment="心情")
    
    project_name = Column(String(100), nullable=True, comment="关联项目")
    related_people = Column(JSON, nullable=True, comment="关联人员（JSON格式）")

    images = Column(JSON, nullable=True, comment="图片URLs（JSON格式）")
    metadata = Column(JSON, default={}, comment="元数据")

    version = Column(Integer, default=1, comment="版本")
    is_deleted = Column(Boolean, default=False, comment="是否删除")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now(), comment="更新时间")


    account = relationship("Account", back_populates="records")
    creator = relationship("User", back_populates="records")
    
    # 明确两个不同的外键关系
    payment_account = relationship(
        "PaymentAccount",
        back_populates="records",
        foreign_keys=[payment_account_id]
    )
    target_payment_account = relationship(
        "PaymentAccount",
        back_populates="transfer_records",
        foreign_keys=[target_payment_account_id]
    )
    
    category = relationship("Category", back_populates="records")
