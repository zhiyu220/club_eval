import os
from dotenv import load_dotenv

# 讀取 .env 檔案
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+pymysql://root:@localhost/club_eval')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask-Mail 設定
    MAIL_SERVER = 'smtp.gmail.com'  # 如果使用 Outlook，請改為 'smtp.office365.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = 'your_email@gmail.com'
    MAIL_PASSWORD = 'your_app_password'  # 需要申請 Gmail 應用程式密碼
    MAIL_DEFAULT_SENDER = 'your_email@gmail.com'
    
    # 📌 測試模式：禁止實際發送 Email
    MAIL_SUPPRESS_SEND = True
    
