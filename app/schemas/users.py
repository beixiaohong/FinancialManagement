from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from enum import Enum

class UserLevel(str, Enum):
    FREE = "free"
    MEMBER = "member"
    PREMIUM = "premium"

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FROZEN = "frozen"

class UserCreate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: str
    verification_code: str

class UserLogin(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: str

class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None

class ResetPassword(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    new_password: str
    verification_code: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
