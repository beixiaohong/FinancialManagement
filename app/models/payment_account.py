# app/models/payment_account.py
from sqlalchemy import DateTime, Column, String, Integer, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.types import DECIMAL
from sqlalchemy.sql import func
from .base import BaseModel
import enum    

class PaymentAccountType(enum.Enum):
    SAVINGS = "savings"
    CREDIT = "credit"
    INVESTMENT = "investment"

class PaymentAccount(BaseModel):
    __tablename__ = "payment_accounts"
    __table_args__ = {'comment': '支付账户表'}

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    
    name = Column(String(100), nullable=False, comment="账户名称")
    account_type = Column(Enum(PaymentAccountType), nullable=False, comment="账户类型")
    description = Column(Text, nullable=True, comment="账户描述")
    
    balance = Column(DECIMAL(15, 2), default=0, comment="账户余额")
    credit_limit = Column(DECIMAL(15, 2), nullable=True, comment="信用额度（仅信用账户）")
    interest_rate = Column(DECIMAL(8, 4), nullable=True, comment="利率（仅理财账户）")
    
    bill_day = Column(Integer, nullable=True, comment="账单日")
    due_day = Column(Integer, nullable=True, comment="还款日")
    
    icon_name = Column(String(50), nullable=True, comment="图标名称")
    color = Column(String(20), default="#1890ff", comment="账户颜色")
    sort_order = Column(Integer, default=0, comment="排序")
    is_active = Column(Boolean, default=True, comment="是否启用")
    
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, comment="账本ID")
    created_by = Column(Integer, ForeignKey("users.id"), comment="创建人")

    version = Column(Integer, default=1, comment="版本")
    is_deleted = Column(Boolean, default=False, comment="是否删除")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now(), comment="更新时间")

    
    account = relationship("Account", back_populates="payment_accounts")
    
    # 普通支付账户对应的记录（明确使用 Record.payment_account_id）
    records = relationship(
        "Record",
        back_populates="payment_account",
        foreign_keys="Record.payment_account_id",
        cascade="all, delete-orphan"
    )
    
    # 转账时作为目标账户被引用的记录集合（明确使用 Record.target_payment_account_id）
    transfer_records = relationship(
        "Record",
        back_populates="target_payment_account",
        foreign_keys="Record.target_payment_account_id",
        cascade="all, delete-orphan"
    )
