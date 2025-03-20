from app import app, db, bcrypt
from models import User

# 設定管理員帳號資訊
admin_username = "admin"
admin_password = "admin123"  # 你可以修改為更安全的密碼

with app.app_context():  # ✅ 確保在 Flask 應用上下文內
    # 加密密碼
    hashed_password = bcrypt.generate_password_hash(admin_password).decode('utf-8')

    # 檢查是否已有 admin 帳號
    if not User.query.filter_by(email=admin_username).first():
        admin_user = User(email=admin_username, password=hashed_password, role="admin")
        db.session.add(admin_user)
        db.session.commit()
        print("✅ 管理員帳號已成功創建！")
    else:
        print("⚠️ 管理員帳號已存在！")
