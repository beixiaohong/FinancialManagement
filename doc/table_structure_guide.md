# 数据库表结构说明和使用指南

## 📊 表结构概览

### 核心业务表（7张表）

| 表名 | 中文名 | 主要功能 | 记录数预估 |
|------|--------|----------|------------|
| `users` | 用户表 | 存储用户基础信息、等级、状态 | 10万+ |
| `accounts` | 账本表 | 存储账本信息、统计数据 | 30万+ |
| `account_members` | 账本成员表 | 管理账本协作关系和权限 | 50万+ |
| `payment_accounts` | 支付账户表 | 管理用户的银行卡、现金等账户 | 100万+ |
| `categories` | 分类表 | 三级分类系统（收支分类） | 1万+ |
| `records` | 记账记录表 | 核心业务数据，每笔账单 | 1000万+ |
| `admin_logs` | 管理员日志表 | 后台操作日志记录 | 10万+ |

## 🏗️ 表结构详细说明

### 1. users - 用户表
**功能**：用户账户管理，支持三级会员体系
```sql
-- 关键字段说明
username VARCHAR(50)     # 唯一用户名，登录凭据
email VARCHAR(100)       # 邮箱，支持邮箱登录
phone VARCHAR(20)        # 手机号，支持短信验证
user_level ENUM          # 用户等级：free/member/premium
user_status ENUM         # 用户状态：active/inactive/frozen
member_expires_at        # 会员到期时间
total_accounts INT       # 账本总数（冗余字段，便于限制检查）
```

**业务逻辑**：
- 免费用户：最多3个账本
- 会员用户：最多10个账本，月费19.9元
- 高级会员：无限账本，年费199元

### 2. accounts - 账本表
**功能**：账本管理，支持个人和协作账本
```sql
-- 关键字段说明
name VARCHAR(100)        # 账本名称
account_type ENUM        # 账本类型：personal/family/team/project
currency VARCHAR(10)     # 默认货币，如CNY、USD
total_income DECIMAL     # 总收入（冗余统计）
total_expense DECIMAL    # 总支出（冗余统计）
owner_id INT            # 账本创建者ID
member_count INT        # 成员数量（冗余统计）
```

**索引设计**：
- 主键索引：id
- 外键索引：owner_id
- 复合索引：(owner_id, created_at) 用于用户账本列表查询

### 3. account_members - 账本成员表
**功能**：账本协作权限管理
```sql
-- 关键字段说明
account_id INT          # 账本ID
user_id INT            # 用户ID
role ENUM              # 角色：admin/editor/viewer
invite_status ENUM     # 邀请状态：pending/accepted/rejected
invite_code VARCHAR    # 邀请码，用于邀请链接
```

**权限说明**：
- **admin**：可删除账本、管理成员、修改设置
- **editor**：可添加、编辑、删除账单
- **viewer**：只能查看账单和报表

**唯一约束**：(account_id, user_id) 防止重复邀请

### 4. payment_accounts - 支付账户表
**功能**：用户资金账户管理
```sql
-- 关键字段说明
account_type ENUM       # 账户类型：savings/credit/investment
balance DECIMAL(15,2)   # 账户余额
credit_limit DECIMAL    # 信用额度（仅信用卡）
bill_day INT           # 账单日（仅信用卡）
due_day INT            # 还款日（仅信用卡）
```

**账户类型**：
- **savings**：储蓄账户（现金、银行卡、余额宝等）
- **credit**：信用账户（信用卡、花呗、借呗等）
- **investment**：理财账户（基金、股票、理财产品等）

### 5. categories - 分类表
**功能**：三级分类系统
```sql
-- 关键字段说明
parent_id INT          # 父分类ID，支持三级分类
level INT              # 分类层级：1/2/3
full_path VARCHAR      # 完整路径，如：餐饮/早餐/包子
is_system BOOLEAN      # 是否系统预设分类
account_id INT         # 账本ID，0表示系统默认分类
```

**分类层级示例**：
```
1级：餐饮 (level=1, parent_id=null)
├─ 2级：早餐 (level=2, parent_id=餐饮ID)
│   ├─ 3级：包子 (level=3, parent_id=早餐ID)
│   └─ 3级：豆浆 (level=3, parent_id=早餐ID)
└─ 2级：午餐 (level=2, parent_id=餐饮ID)
```

### 6. records - 记账记录表 ⭐
**功能**：核心业务数据，每笔收支记录
```sql
-- 关键字段说明
record_type ENUM         # 记录类型：income/expense/transfer
amount DECIMAL(15,2)     # 金额，精确到分
record_date DATETIME     # 记录日期，支持时区
payment_account_id INT   # 支付账户ID
category_id INT         # 分类ID
tags TEXT               # 标签（JSON格式）
location VARCHAR        # 消费地点
project_name VARCHAR    # 关联项目
related_people TEXT     # 关联人员（JSON格式）
```

**重要索引**：
```sql
-- 查询优化索引
INDEX idx_account_date (account_id, record_date)      # 账本记录查询
INDEX idx_user_date (creator_id, record_date)         # 用户记录查询  
INDEX idx_category (category_id)                      # 分类统计查询
INDEX idx_payment_account (payment_account_id)        # 账户流水查询
```

### 7. admin_logs - 管理员日志表
**功能**：后台管理操作审计
```sql
-- 关键字段说明
admin_id INT           # 管理员用户ID
action VARCHAR         # 操作类型：user_level_change、user_reset等
target_type VARCHAR    # 操作目标：user、account等
old_data JSON         # 操作前数据
new_data JSON         # 操作后数据
ip_address VARCHAR    # 操作IP地址
```

## 🚀 快速启动指南

### 1. 环境准备
```bash
# 安装MySQL和Redis（使用Docker）
docker-compose up -d

# 或手动安装
# MySQL 8.0+
# Redis 6.0+
```

### 2. 项目安装
```bash
# 克隆项目
git clone <项目地址>
cd accounting_backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置文件
```bash
# 创建 .env 文件
cp .env.example .env

# 修改数据库连接配置
DATABASE_URL=mysql+pymysql://2vsjdcaJCGZmCUa.root:4sAP1moo0P3iVnUD@gateway01.ap-northeast-1.prod.aws.tidbcloud.com:4000/accounting?charset=utf8mb4
```

### 4. 启动服务
```bash
# 启动FastAPI服务
python run.py

# 或使用uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. 验证安装
```bash
# 访问API文档
http://localhost:8000/docs

# 检查数据库表
# 在MySQL中查看表是否创建成功
SHOW TABLES;
```

## 📈 性能优化建议

### 1. 数据库优化
```sql
-- 创建必要的索引
ALTER TABLE records ADD INDEX idx_account_date_type (account_id, record_date, record_type);
ALTER TABLE records ADD INDEX idx_amount_range (account_id, amount);
ALTER TABLE users ADD INDEX idx_level_status (user_level, user_status);

-- 分区表（当records表超过1000万条时）
ALTER TABLE records PARTITION BY RANGE (YEAR(record_date)) (
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026)
);
```

### 2. 缓存策略
```python
# Redis缓存关键数据
- 用户信息：cache_key = f"user:{user_id}"
- 账本统计：cache_key = f"account_stats:{account_id}"
- 分类数据：cache_key = f"categories:{account_id}"
```

### 3. 数据归档
```sql
-- 定期归档历史数据（建议保留2年活跃数据）
CREATE TABLE records_archive LIKE records;
-- 将2年前的数据移动到归档表
```

## 🔧 常见问题和解决方案

### 1. 字符编码问题
```python
# 确保数据库连接使用UTF8MB4
DATABASE_URL = "mysql+pymysql://user:pass@host:port/db?charset=utf8mb4"

# 建表时指定字符集
CREATE DATABASE accounting_app CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 时区处理
```python
# 服务器设置UTC时区，应用层转换
import pytz
from datetime import datetime

# 存储时使用UTC
utc_time = datetime.utcnow()

# 显示时转换为用户时区
user_timezone = pytz.timezone('Asia/Shanghai')
local_time = utc_time.replace(tzinfo=pytz.UTC).astimezone(user_timezone)
```

### 3. 大数据量查询优化
```python
# 使用分页查询
def get_records_paginated(db: Session, account_id: int, skip: int, limit: int):
    return db.query(Record)\
             .filter(Record.account_id == account_id)\
             .order_by(Record.record_date.desc())\
             .offset(skip)\
             .limit(limit)\
             .all()

# 使用聚合查询替代循环查询
def get_account_statistics(db: Session, account_id: int):
    result = db.query(
        func.sum(case((Record.record_type == 'income', Record.amount), else_=0)).label('total_income'),
        func.sum(case((Record.record_type == 'expense', Record.amount), else_=0)).label('total_expense'),
        func.count().label('total_records')
    ).filter(Record.account_id == account_id).first()
    return result
```

## 📝 数据迁移和备份

### 1. 数据库迁移
```bash
# 使用Alembic管理数据库版本
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 2. 数据备份
```bash
# 每日自动备份脚本
mysqldump -u username -p accounting_app > backup_$(date +%Y%m%d).sql

# 恢复数据
mysql -u username -p accounting_app < backup_20241201.sql
```

这个数据库设计已经考虑了扩展性、性能和数据一致性，可以支持百万级用户和千万级记录的业务场景。