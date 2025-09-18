# app/models/category.py
from sqlalchemy import Column, String, Integer, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel

class Category(BaseModel):
    __tablename__ = "categories"
    __table_args__ = {'comment': '分类表（三级分类）'}

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

    # 关联关系
    account = relationship("Account", back_populates="categories")
    parent = relationship("Category", remote_side="Category.id", back_populates="children")
    children = relationship("Category", back_populates="parent")
    records = relationship("Record", back_populates="category")
