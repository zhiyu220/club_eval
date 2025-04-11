from app import db
from app import app

with app.app_context():
    db.create_all()
    print("✅ 資料表建立完成")
