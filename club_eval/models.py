from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import UserMixin
from datetime import datetime, timezone

db = SQLAlchemy()
bcrypt = Bcrypt()

# 使用者模型
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id', ondelete="SET NULL"), nullable=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))  # ✅ 確保時間格式正確

    club = db.relationship('Club', backref=db.backref('users', lazy=True))

# 公告模型
class Announcement(db.Model):
    __tablename__ = 'announcement'  # ✅ 改為複數名稱以保持一致性
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))  # ✅ 統一使用 `datetime.now(timezone.utc)`
    file_path = db.Column(db.String(300))
    carousel_image = db.Column(db.String(300), nullable=True)  # ✅ 確保輪播圖可以為空
    in_carousel = db.Column(db.Boolean, default=False)  # ✅ 是否加入輪播

# 投票模型
class Vote(db.Model):
    __tablename__ = 'votes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)  # ✅ 指向 `user.id`
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id', ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref=db.backref('votes', lazy=True, cascade="all, delete"))
    club = db.relationship('Club', backref=db.backref('votes', lazy=True, cascade="all, delete"))# 投票時間控制

class VotingConfig(db.Model):
    __tablename__ = 'voting_config'
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)

# 輪播管理
class Carousel(db.Model):
    __tablename__ = 'carousel'
    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(300), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, unique=True)  # ✅ 控制輪播順序

# 評鑑辦法管理
class EvaluationRule(db.Model):
    __tablename__ = 'evaluation_rules'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    file_path = db.Column(db.String(300))

# 社團管理
class Club(db.Model):
    __tablename__ = 'clubs'
    id = db.Column(db.Integer, primary_key=True)
    club_name = db.Column(db.String(150), unique=True, nullable=False)
    club_category = db.Column(db.Enum(
        '學術文藝性', '康樂性', '聯誼性', '服務性', '義工性', '體育性', '自治性'
    ), nullable=False)

#表單下載
class EvaluationFile(db.Model):
    __tablename__ = 'evaluation_files'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)  # 檔案名稱
    file_path = db.Column(db.String(500), nullable=False) # 存儲的路徑
    uploaded_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))  # 上傳時間

#行事曆模型
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=True)
    description = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "start": self.start.isoformat(),
            "end": self.end.isoformat() if self.end else None,
            "description": self.description
        }
