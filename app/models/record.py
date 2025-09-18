from sqlalchemy import Column, String, Integer, ForeignKey, Enum, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.types import DECIMAL
from .base import BaseModel
import enum

class RecordType(enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"

class Record(BaseModel):
    __tablename__ = "records"
    __table_args__ = {'comment': '记账记录表'}
    
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
    
    tags = Column(Text, nullable=True, comment="标签（JSON格式）")
    location = Column(String(255), nullable=True, comment="消费地点")
    weather = Column(String(50), nullable=True, comment="天气情况")
    mood = Column(String(50), nullable=True, comment="心情")
    
    project_name = Column(String(100), nullable=True, comment="关联项目")
    related_people = Column(Text, nullable=True, comment="关联人员（JSON格式）")
    
    images = Column(Text, nullable=True, comment="图片URLs（JSON格式）")
    
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
