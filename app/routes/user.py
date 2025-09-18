from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User, UserLevel, UserStatus
from app.schemas.users import UserCreate, UserLogin, UserUpdate, ResetPassword, Token
from app.core.security import get_password_hash, verify_password, create_access_token, SUPER_VERIFICATION_CODE

users_router = APIRouter(prefix="/users", tags=["users"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 模拟验证码验证（开发阶段支持超级验证码）
def verify_code(code: str) -> bool:
    return code == SUPER_VERIFICATION_CODE

# 注册
@users_router.post("/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if not (user.email or user.phone):
        raise HTTPException(status_code=400, detail="必须提供邮箱或手机号")
    if not verify_code(user.verification_code):
        raise HTTPException(status_code=400, detail="验证码错误")

    query = db.query(User)
    if user.email:
        if query.filter(User.email == user.email).first():
            raise HTTPException(status_code=400, detail="邮箱已被注册")
    if user.phone:
        if query.filter(User.phone == user.phone).first():
            raise HTTPException(status_code=400, detail="手机号已被注册")

    new_user = User(
        email=user.email,
        phone=user.phone,
        password_hash=get_password_hash(user.password),
        user_level=UserLevel.FREE,
        user_status=UserStatus.ACTIVE
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({"sub": new_user.username})
    return Token(access_token=token)

# 登录
@users_router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    if not (user.email or user.phone):
        raise HTTPException(status_code=400, detail="必须提供邮箱或手机号")

    query = db.query(User)
    db_user = None
    if user.email:
        db_user = query.filter(User.email == user.email).first()
    elif user.phone:
        db_user = query.filter(User.phone == user.phone).first()

    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="邮箱/手机号或密码错误")

    token = create_access_token({"sub": db_user.username})
    return Token(access_token=token)

# 修改用户资料
@users_router.put("/profile", response_model=dict)
def update_profile(update: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_db)):
    # 这里可用 OAuth2 获取 current_user
    # 简化示例，不加 OAuth2
    user = db.query(User).first()  # 临时取第一个用户
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    for field, value in update.dict(exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return {"msg": "资料更新成功"}

# 找回密码
@users_router.post("/reset-password", response_model=dict)
def reset_password(data: ResetPassword, db: Session = Depends(get_db)):
    if not (data.email or data.phone):
        raise HTTPException(status_code=400, detail="必须提供邮箱或手机号")
    if not verify_code(data.verification_code):
        raise HTTPException(status_code=400, detail="验证码错误")

    query = db.query(User)
    user = None
    if data.email:
        user = query.filter(User.email == data.email).first()
    elif data.phone:
        user = query.filter(User.phone == data.phone).first()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.password_hash = get_password_hash(data.new_password)
    db.commit()
    return {"msg": "密码重置成功"}
