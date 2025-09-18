from sqlalchemy import Column, String, Integer, Enum, DateTime, Text
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class UserLevel(enum.Enum):
    FREE = "free"
    MEMBER = "member"
    PREMIUM = "premium"

class UserStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FROZEN = "frozen"

class User(BaseModel):
    __tablename__ = "users"
    __table_args__ = {'comment': '用户表'}
    
    username = Column(String(50), unique=True, index=True, nullable=False, comment="用户名")
    email = Column(String(100), unique=True, index=True, nullable=True, comment="邮箱")
    phone = Column(String(20), unique=True, index=True, nullable=True, comment="手机号")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    
    nickname = Column(String(50), nullable=True, comment="昵称")
    avatar_url = Column(String(255), nullable=True, comment="头像URL")
    bio = Column(Text, nullable=True, comment="个人简介")
    
    user_level = Column(Enum(UserLevel), default=UserLevel.FREE, comment="用户等级")
    user_status = Column(Enum(UserStatus), default=UserStatus.ACTIVE, comment="用户状态")
    
    member_expires_at = Column(DateTime(timezone=True), nullable=True, comment="会员到期时间")
    
    total_accounts = Column(Integer, default=0, comment="账本总数")
    total_records = Column(Integer, default=0, comment="记录总数")
    last_login_at = Column(DateTime(timezone=True), nullable=True, comment="最后登录时间")
    
    accounts = relationship("Account", back_populates="owner", cascade="all, delete-orphan")
    
    # 明确使用 AccountMember.user_id，避免与 invited_by_id 歧义
    account_members = relationship(
        "AccountMember",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="AccountMember.user_id",
        overlaps="invited_members,invited_by"
    )
    
    # 该用户作为邀请人的反向关系（使用 invited_by_id）
    invited_members = relationship(
        "AccountMember",
        back_populates="invited_by",
        cascade="all, delete-orphan",
        foreign_keys="AccountMember.invited_by_id",
        overlaps="account_members,invited_by"
    )
    
    records = relationship("Record", back_populates="creator", cascade="all, delete-orphan")
