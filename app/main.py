# app/main.py
from fastapi import FastAPI
from app.core.init_db import init_database
from app.routes import user

app = FastAPI(title="记账应用API", version="1.0.0")
app.include_router(user.users_router)

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    init_database()

@app.get("/")
async def root():
    return {"message": "记账应用API服务启动成功！"}