from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# 在这里导入所有模型，确保 relationship("Account") 能找到
from .user import User
from .account import Account
from .account_member import AccountMember
from .category import Category
from .payment_account import PaymentAccount
from .record import Record
from .admin_log import AdminLog
