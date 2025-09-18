# app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base
from app.core.config import settings
import os

# 支持 TiDB Cloud 的 CA 文件（生产）或本地关闭证书校验（测试）
connect_args = {}
TIDB_CA_PATH = os.getenv("TIDB_CA_PATH")  # 可在环境中设置 CA 路径

if "mysql+pymysql" in settings.DATABASE_URL:
    if TIDB_CA_PATH:
        connect_args["ssl"] = {"ca": TIDB_CA_PATH}
    else:
        # 本地测试临时关闭证书验证（生产不要这么做）
        connect_args["ssl"] = {"ssl_verify_cert": False, "ssl_verify_identity": False}

engine = create_engine(
    settings.DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成！")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
