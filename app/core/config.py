# app/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "记账应用"
    APP_VERSION: str = "1.0.0"
    
    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL") 
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "changeme")
    # JWT配置
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379"
    
    # 文件上传配置
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    class Config:
        env_file = ".env"

settings = Settings()