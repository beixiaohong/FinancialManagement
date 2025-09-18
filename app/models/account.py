# app/models/account.py
from sqlalchemy import Column, String, Integer, Text, ForeignKey, Enum
from sqlalchemy.types import DECIMAL  # 修改这行
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class AccountType(enum.Enum):
    PERSONAL = "personal"    # 个人账本
    FAMILY = "family"       # 家庭账本  
    TEAM = "team"          # 团队账本
    PROJECT = "project"     # 项目账本

class Account(BaseModel):
    __tablename__ = "accounts"
    __table_args__ = {'comment': '账本表'}
    
    # 基础信息
    name = Column(String(100), nullable=False, comment="账本名称")
    description = Column(Text, nullable=True, comment="账本描述")
    account_type = Column(Enum(AccountType), default=AccountType.PERSONAL, comment="账本类型")
    
    # 设置信息
    currency = Column(String(10), default="CNY", comment="默认货币")
    icon_url = Column(String(255), nullable=True, comment="账本图标")
    color = Column(String(20), default="#1890ff", comment="账本颜色")
    
    # 统计信息 - 使用DECIMAL替代Decimal
    total_income = Column(DECIMAL(15, 2), default=0, comment="总收入")
    total_expense = Column(DECIMAL(15, 2), default=0, comment="总支出")
    total_records = Column(Integer, default=0, comment="记录总数")
    member_count = Column(Integer, default=1, comment="成员数量")
    
    # 创建者
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="创建者ID")
    
    # 关联关系
    owner = relationship("User", back_populates="accounts")
    members = relationship("AccountMember", back_populates="account", cascade="all, delete-orphan")
    payment_accounts = relationship("PaymentAccount", back_populates="account", cascade="all, delete-orphan")
    records = relationship("Record", back_populates="account", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="account", cascade="all, delete-orphan")
