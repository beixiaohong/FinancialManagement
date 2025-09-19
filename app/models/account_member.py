## app/models/account_member.py
from sqlalchemy import Column, Integer, ForeignKey, Enum, DateTime, String, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel
import enum

class MemberRole(enum.Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"

class InviteStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"

    

class AccountMember(BaseModel):
    __tablename__ = "account_members"
    __table_args__ = {'comment': '账本成员表'}

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, comment="账本ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    invited_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="邀请人ID")
    
    role = Column(Enum(MemberRole), default=MemberRole.VIEWER, comment="成员角色")
    invite_status = Column(Enum(InviteStatus), default=InviteStatus.PENDING, comment="邀请状态")
    
    invite_code = Column(String(50), unique=True, nullable=True, comment="邀请码")
    invited_at = Column(DateTime(timezone=True), nullable=True, comment="邀请时间")
    accepted_at = Column(DateTime(timezone=True), nullable=True, comment="接受时间")

    version = Column(Integer, default=1, comment="版本")
    is_deleted = Column(Boolean, default=False, comment="是否删除")
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), comment="加入时间")
    
    # 关系
    account = relationship("Account", back_populates="members")
    
    # 成员对应用户（明确 user_id）
    user = relationship(
        "User",
        back_populates="account_members",
        foreign_keys=[user_id],
        overlaps="invited_members,invited_by"
    )
    
    # 邀请人（明确 invited_by_id）
    invited_by = relationship(
        "User",
        back_populates="invited_members",
        foreign_keys=[invited_by_id],
        overlaps="account_members,invited_by"
    )
