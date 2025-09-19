# app/models/category.py
from sqlalchemy import Column, String, DateTime, Integer, Numeric, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel

class Category(BaseModel):
    __tablename__ = "categories"
    __table_args__ = {'comment': '分类表（三级分类）'}

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)

    # 基础信息
    name = Column(String(100), nullable=False, comment="分类名称")
    description = Column(Text, nullable=True, comment="分类描述")

    # 层级关系
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True, comment="父分类ID")
    level = Column(Integer, nullable=False, comment="分类层级(1/2/3)")
    full_path = Column(String(255), nullable=True, comment="完整路径")

    # 显示设置
    icon_name = Column(String(50), nullable=True, comment="图标名称")
    color = Column(String(20), default="#1890ff", comment="分类颜色")
    sort_order = Column(Integer, default=0, comment="排序")
    is_active = Column(Boolean, default=True, comment="是否启用")
    is_system = Column(Boolean, default=False, comment="是否系统预设")

    # 关联账本，可空
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, comment="账本ID")
    created_by = Column(Integer, ForeignKey("users.id"), comment="创建人")

    record_count = Column(Integer, default=0, comment="记录数量")
    total_amount = Column(Numeric(12, 2), default=0, comment="总计数据")

    version = Column(Integer, default=1, comment="版本")
    is_deleted = Column(Boolean, default=False, comment="是否删除")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now(), comment="更新时间")

    # 关联关系
    account = relationship("Account", back_populates="categories")
    parent = relationship("Category", remote_side="Category.id", back_populates="children")
    children = relationship("Category", back_populates="parent")
    records = relationship("Record", back_populates="category")
