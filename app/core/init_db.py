from sqlalchemy.orm import Session
from app.core.database import SessionLocal, create_tables
from app.models.category import Category
from app.models.user import User, UserLevel
from app.models.account import Account
from app.core.security import get_password_hash

def init_database():
    create_tables()
    db = SessionLocal()
    try:
        init_default_categories(db)
        db.commit()
        print("数据库初始化完成！")
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        db.rollback()
    finally:
        db.close()
        

def init_default_categories(db: Session):
    """初始化默认系统分类"""
    # 检查是否已有系统分类

    if db.query(Category).filter(Category.is_system == True).first():
        return

    default_categories = [
        {"name": "餐饮", "level": 1, "icon_name": "restaurant", "color": "#ff6b6b"},
        {"name": "交通", "level": 1, "icon_name": "car", "color": "#4ecdc4"},
        {"name": "购物", "level": 1, "icon_name": "shopping", "color": "#45b7d1"},
        {"name": "娱乐", "level": 1, "icon_name": "game", "color": "#f9ca24"},
        {"name": "医疗", "level": 1, "icon_name": "medical", "color": "#6c5ce7"},
        {"name": "教育", "level": 1, "icon_name": "book", "color": "#a29bfe"},
        {"name": "居住", "level": 1, "icon_name": "home", "color": "#fd79a8"},
        {"name": "工资", "level": 1, "icon_name": "money", "color": "#00b894"},
        {"name": "其他", "level": 1, "icon_name": "more", "color": "#636e72"},
    ]
    # 1. 确保管理员用户存在
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=get_password_hash("admin123"),
            nickname="系统管理员",
            user_level=UserLevel.PREMIUM,
            user_status='ACTIVE'        # 激活状态
        )
        db.add(admin)
        db.commit()
        print("创建默认管理员用户: admin/admin123")


    # 2. 确保默认账户存在
    system_account = db.query(Account).filter_by(name='默认账户').first()
    if not system_account:
        system_account = Account(
            name='默认账户',
            owner_id=admin.id  # 关联管理员
        )
        db.add(system_account)
        db.commit()  # 生成 id

    # 3. 创建默认分类
    for cat_data in default_categories:
        existing = db.query(Category).filter_by(
            name=cat_data["name"], account_id=system_account.id
        ).first()
        if not existing:
            category = Category(
                name=cat_data["name"],
                level=cat_data["level"],
                icon_name=cat_data["icon_name"],
                color=cat_data["color"],
                is_system=True,
                account_id=system_account.id
            )
            db.add(category)

    db.commit()
    print("数据库初始化完成！")


