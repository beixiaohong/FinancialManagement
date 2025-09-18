# FastAPI 项目结构建议

```
accounting_backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI应用入口
│   ├── core/                   # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py          # 配置文件
│   │   ├── security.py        # 安全相关(JWT, 密码加密)
│   │   └── database.py        # 数据库连接
│   ├── api/                    # API路由
│   │   ├── __init__.py
│   │   ├── deps.py            # 依赖注入
│   │   ├── v1/                # API版本1
│   │   │   ├── __init__.py
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py    # 认证相关
│   │   │   │   ├── users.py   # 用户管理
│   │   │   │   ├── accounts.py # 账本管理
│   │   │   │   ├── records.py  # 记账记录
│   │   │   │   └── admin.py    # 管理后台
│   │   │   └── api.py         # 路由汇总
│   ├── models/                 # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── account.py
│   │   ├── record.py
│   │   └── base.py            # 基础模型
│   ├── schemas/               # Pydantic模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── account.py
│   │   └── record.py
│   ├── crud/                  # 数据库操作
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── account.py
│   │   └── record.py
│   ├── services/              # 业务逻辑
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── account_service.py
│   │   └── analytics_service.py
│   └── utils/                 # 工具函数
│       ├── __init__.py
│       ├── common.py
│       └── validators.py
├── alembic/                   # 数据库迁移
├── tests/                     # 测试文件
├── requirements.txt
└── pyproject.toml

# 核心依赖包
requirements.txt:
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9
redis==5.0.1
celery==5.3.4
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
pydantic[email]==2.5.0
pydantic-settings==2.1.0
