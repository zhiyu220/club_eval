from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from models import db, bcrypt, User, Announcement, Vote, Carousel, EvaluationRule, Club, VotingConfig,EvaluationFile,Event
from config import Config
import random
import string
import os
import re
import unicodedata
from flask_mail import Mail, Message
from flask import Flask, render_template, request, redirect, flash, url_for
from datetime import datetime, timezone
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
mail = Mail(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

UPLOAD_FOLDER = 'uploads'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 📌 自訂 secure_filename，允許國字
def custom_secure_filename(filename):
    name, ext = os.path.splitext(filename)
    name = re.sub(r'[\/:*?"<>|]', '', name) 
    name = unicodedata.normalize('NFKC', name).strip().replace(" ", "_")
    return f"{name}{ext}"

def send_email(email, password):
    msg = Message("元智大學社團評鑑系統帳號資訊",
                  recipients=[email])
    msg.body = f"""
    親愛的使用者，

    您的帳號已成功建立！請使用以下資訊登入：
    
    登入 Email: {email}
    預設密碼: {password}

    請登入後立即更改密碼，確保帳號安全。

    此信件由系統自動發送，請勿回覆。

    社團評鑑系統團隊
    """
    
    if app.config['MAIL_SUPPRESS_SEND']:
        print("📩 [測試模式] 模擬發送 Email：")
        print(f"🔹 收件人: {email}")
        print(f"🔹 信件內容:\n{msg.body}")
    else:
        try:
            mail.send(msg)
            print(f"✅ Email 已成功發送至 {email}")
        except Exception as e:
            print(f"❌ Email 發送失敗: {str(e)}")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    announcements = Announcement.query.order_by(Announcement.id.desc()).limit(5).all()
    return render_template('index.html', announcements=announcements)

@app.route('/events')
def get_events():
    events = Event.query.all()
    return jsonify([event.to_dict() for event in events])

@app.route('/login', methods=['GET', 'POST'])
def login():
    session.pop('_flashes', None)
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash('✅ 登入成功！', 'success')

            # `admin` 可以進入後台，但也可以正常使用網站
            return redirect(url_for('index'))
        else:
            flash('❌ Email 或密碼錯誤！', 'danger')

    return render_template('login.html')

@app.route('/admin_dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('⚠️ 你沒有權限訪問此頁面！', 'danger')
        return redirect(url_for('index'))
    
    # 📌 嘗試從資料庫獲取投票設定
    voting_config = VotingConfig.query.first()

    # 📌 如果沒有記錄，則初始化預設值
    if not voting_config:
        voting_config = VotingConfig(start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc))
        db.session.add(voting_config)
        db.session.commit()

    if request.method == 'POST':
        action = request.form.get('action')  # 📌 確保 `action` 變數有定義

          # 📌 單一新增用戶
        if action == 'add_user':
            club_id = request.form.get('club_id')
            full_name = request.form['full_name']
            email = request.form['email'].strip()

            if User.query.filter_by(email=email).first():
                flash(f'⚠️ {email} 已存在，略過', 'warning')
            else:
                password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                new_user = User(
                    club_id=club_id,
                    full_name=full_name,
                    email=email,
                    password=hashed_password,
                    role="user",
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(new_user)
                db.session.commit()

                send_email(email, password)  # 📌 確保 `send_email()` 只在成功時執行
                flash('✅ 用戶已新增並寄送密碼郵件！', 'success')

        # 📌 批量新增用戶
        elif action == 'add_users':
            emails = request.form['emails'].split(',')
            club_id = request.form.get('club_id')  # 📌 允許批量新增時設定 `club_id`
            new_users = []
            sent_emails = []

            for email in emails:
                email = email.strip()
                if not User.query.filter_by(email=email).first():
                    password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

                    new_user = User(
                        club_id=club_id,
                        full_name="未設定",
                        email=email,
                        password=hashed_password,
                        role="user",
                        created_at=datetime.now(timezone.utc)
                    )
                    new_users.append(new_user)
                    sent_emails.append((email, password))

            if new_users:
                db.session.bulk_save_objects(new_users)
                db.session.commit()
                for email, password in sent_emails:
                    send_email(email, password)
                flash(f'✅ 批量新增 {len(new_users)} 位用戶並寄送密碼郵件！', 'success')
            else:
                flash('⚠️ 所有用戶皆已存在，未新增', 'warning')

        # 📌 刪除用戶
        elif action == 'delete_user':
            user_id = request.form['user_id']
            user = User.query.get(user_id)
            if user:
                db.session.delete(user)
                db.session.commit()
                flash('✅ 用戶已刪除！', 'success')
        # 📌 單一新增 & 批量新增社團
        elif action == 'add_club_batch':
            club_category = request.form.get('club_category')
            single_club_name = request.form.get('single_club_name')
            batch_club_names = request.form.get('batch_club_names')

            if single_club_name:
                if not Club.query.filter_by(club_name=single_club_name).first():
                    db.session.add(Club(club_name=single_club_name, club_category=club_category))
                    db.session.commit()
                    flash(f'✅ 新增社團 {single_club_name}', 'success')

            elif batch_club_names:
                count = 0
                for club_name in batch_club_names.split("\n"):
                    club_name = club_name.strip()
                    if club_name and not Club.query.filter_by(club_name=club_name).first():
                        db.session.add(Club(club_name=club_name, club_category=club_category))
                        count += 1
                if count > 0:
                    db.session.commit()
                    flash(f'✅ 批量新增 {count} 個社團', 'success')

         # 📌 刪除社團
        elif action == 'delete_club':
            club_id = request.form.get('club_id')
            if club_id:
                club = Club.query.get(club_id)
                if club:
                    db.session.delete(club)
                    db.session.commit()
                    flash('✅ 社團已刪除', 'success')
                else:
                    flash('⚠️ 無效的社團 ID', 'danger')
            else:
                flash('⚠️ 未提供社團 ID', 'danger')
                
        # 📌 更新投票時間
        elif action == 'update_voting_time':
            start_time = datetime.fromisoformat(request.form['start_time']).replace(tzinfo=timezone.utc)
            end_time = datetime.fromisoformat(request.form['end_time']).replace(tzinfo=timezone.utc)
            
            voting_config.start_time = start_time
            voting_config.end_time = end_time
            db.session.commit()
            flash('✅ 投票時間已更新！', 'success')

    # 取得所有年份
    years = db.session.query(db.func.year(User.created_at)).distinct().order_by(db.desc(db.func.year(User.created_at))).all()
    years = [year[0] for year in years]  # 提取年份數據
    
    # 📌 取得投票結果
    voting_config = VotingConfig.query.first()
    if not voting_config:
        voting_config = VotingConfig(start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc))
        db.session.add(voting_config)
        db.session.commit()
        
    vote_results = db.session.query(Club.club_name, db.func.count(Vote.id)).join(Vote, Club.id == Vote.club_id).group_by(Club.id).order_by(db.func.count(Vote.id).desc()).all()
    
    clubs = Club.query.all()
    users = User.query.all()
    return render_template('admin_dashboard.html', users=users, clubs=clubs,voting_config=voting_config, vote_results=vote_results, enumerate=enumerate)  # 📌 確保 `clubs` 變數傳遞到前端

@app.route('/vote', methods=['GET', 'POST'])
@login_required
def vote():
    # 取得目前時間 (UTC)
    now = datetime.now(timezone.utc)

    # 取得投票時間
    voting_config = VotingConfig.query.first()

    if voting_config:
        # 確保時間與 UTC 對齊
        start_time_utc = voting_config.start_time.astimezone(timezone.utc)
        end_time_utc = voting_config.end_time.astimezone(timezone.utc)

        # 檢查投票是否在開放時間內
        if now < start_time_utc or now > end_time_utc:
            return render_template(
                'vote.html',
                voting_config=voting_config,
                now=now,
                clubs=[],
                user=current_user,
                voting_error=f"⏳ 投票尚未開放或已結束！\n🕒 開放時間：{start_time_utc.strftime('%Y-%m-%d %H:%M')} ~ {end_time_utc.strftime('%Y-%m-%d %H:%M')}"
            )
    else:
        return render_template(
            'vote.html',
            voting_config=None,
            now=now,
            clubs=[],
            user=current_user,
            voting_error="⚠️ 投票時間未設定！請聯繫管理員。"
        )

    # 檢查用戶是否已投票 (限制 2 票)
    user_votes = Vote.query.filter_by(user_id=current_user.id).count()
    if user_votes >= 2:
        return render_template(
            'vote.html',
            voting_config=voting_config,
            now=now,
            clubs=[],
            user=current_user,
            voting_error="⚠️ 你已經投過票，無法再次投票！"
        )

    # 取得可投票的社團 (排除自己社團)
    clubs = Club.query.filter(Club.id != current_user.club_id).all()

    if request.method == 'POST':
        action = request.form.get('action')

        # 📌 提交投票
        if action == 'submit_vote':
            vote_club_1 = request.form.get('vote_club_1')
            vote_club_2 = request.form.get('vote_club_2')

            if not vote_club_1:
                flash("⚠️ 至少要選擇一個社團投票！", "danger")
                return redirect(url_for('vote'))

            # 轉換為數字並驗證
            try:
                vote_club_1 = int(vote_club_1)
                if vote_club_2:
                    vote_club_2 = int(vote_club_2)
            except ValueError:
                flash("⚠️ 無效的社團選擇！", "danger")
                return redirect(url_for('vote'))

            # 確保不投給自己社團
            if vote_club_1 == current_user.club_id or (vote_club_2 and vote_club_2 == current_user.club_id):
                flash("⚠️ 不能投票給自己所屬的社團！", "danger")
                return redirect(url_for('vote'))

            # 確保不投重複的社團
            if vote_club_2 and vote_club_1 == vote_club_2:
                flash("⚠️ 不能將兩票都投給同一個社團！", "danger")
                return redirect(url_for('vote'))

            # 確保社團 ID 存在
            valid_club_ids = {club.id for club in clubs}
            if vote_club_1 not in valid_club_ids or (vote_club_2 and vote_club_2 not in valid_club_ids):
                flash("⚠️ 選擇的社團不存在！", "danger")
                return redirect(url_for('vote'))

            # 新增投票記錄
            db.session.add(Vote(user_id=current_user.id, club_id=vote_club_1))
            if vote_club_2:
                db.session.add(Vote(user_id=current_user.id, club_id=vote_club_2))

            db.session.commit()
            flash("✅ 投票成功！", "success")
            return redirect(url_for('index'))

    return render_template('vote.html', voting_config=voting_config, now=now, clubs=clubs, user=current_user)

@app.route('/evaluation_rules', methods=['GET', 'POST'])
def evaluation_rules():
    evaluation_rule = EvaluationRule.query.first()
    if not evaluation_rule:
        evaluation_rule = EvaluationRule(title="評鑑辦法標題", content="這是評鑑辦法內容")
        db.session.add(evaluation_rule)
        db.session.commit()

    files = EvaluationFile.query.order_by(EvaluationFile.filename.asc()).all()

    return render_template('evaluation_rules.html', evaluation_rule=evaluation_rule, files=files)

@app.route('/rename_file', methods=['POST'])
@login_required
def rename_file():
    file_id = request.form.get('file_id')
    new_name = request.form.get('new_name').strip()  # 新的檔案名稱

    file = EvaluationFile.query.get(file_id)
    if not file:
        flash("⚠️ 找不到該檔案！", "danger")
        return redirect(url_for('evaluation_rules'))

    # 解析原檔案名稱，保留副檔名
    original_filename = file.filename
    name, ext = os.path.splitext(original_filename)
    
    # ✅ 允許中文檔名
    new_filename = custom_secure_filename(new_name) + ext

    new_filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
    if os.path.exists(new_filepath):
        flash("⚠️ 這個名稱已經存在，請選擇其他名稱！", "danger")
        return redirect(url_for('evaluation_rules'))

    # 重新命名檔案
    old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    os.rename(old_filepath, new_filepath)

    # 更新資料庫
    file.filename = new_filename
    db.session.commit()

    flash("✅ 檔案名稱已成功變更！", "success")
    return redirect(url_for('evaluation_rules'))

# 上傳檔案
@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash("⚠️ 未選擇檔案", "danger")
        return redirect(url_for('evaluation_rules'))

    file = request.files['file']
    
    if file.filename == '':
        flash("⚠️ 檔案名稱無效", "danger")
        return redirect(url_for('evaluation_rules'))

    filename = custom_secure_filename(file.filename)  # 🔥 確保名稱安全
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    counter = 1
    while os.path.exists(file_path):
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{counter}{ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        counter += 1

    try:
        file.save(file_path)
        print(f"✅ [DEBUG] 檔案儲存成功：{file_path}")  # Debug

        # 📌 確保 `uploaded_at` 也儲存
        new_file = EvaluationFile(filename=filename, file_path=file_path, uploaded_at=datetime.now())
        db.session.add(new_file)
        db.session.commit()
        print(f"✅ [DEBUG] 成功儲存到資料庫: {filename}")  # Debug
        
        flash("✅ 檔案上傳成功！", "success")

    except Exception as e:
        flash(f"❌ 檔案上傳失敗：{str(e)}", "danger")
        return redirect(url_for('evaluation_rules'))

    return redirect(url_for('evaluation_rules'))  # 📌 重新導向以刷新頁面

# 下載檔案（允許所有人下載）
@app.route('/downloads/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    
@app.route('/logout')
@login_required
def logout():
    session.pop('_flashes', None)  # 清除舊的 flash 訊息
    logout_user()
    flash("🔑 你已成功登出！", "success")
    return redirect(url_for('index'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
