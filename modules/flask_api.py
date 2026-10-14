from flask import Flask, render_template, request, jsonify, session
import os
from PIL import Image
from werkzeug.utils import secure_filename
import uuid
import bcrypt
from datetime import datetime

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"))

app.secret_key = "123456"

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TEMPLATES_AUTO_RELOAD'] = False

# 数据库模块（启动时自动建库建表）
from modules import db
db.init_db()

# CLIP 模型（启动时加载一次）
from modules.clip_core import load_clip_model, get_image_feature, cosine_sim
from modules.scene_classify import classify_scene
from modules.text_preprocess import get_scene_tokens
model, preprocess, device = load_clip_model()

# LLM 文案生成（通过 Ollama HTTP 调用）
from modules.caption_lib import generate_caption


def _client_ip():
    return request.remote_addr or "unknown"


def _current_user():
    """根据 session 返回当前登录用户字典，未登录返回 None。"""
    uid = session.get('user_id')
    if not uid:
        return None
    return db.query_one("SELECT id, username, role, nickname, avatar FROM users WHERE id=%s", (uid,))


def log_action(user_id, action, detail=""):
    """写操作日志（失败不影响主流程）。"""
    try:
        db.execute(
            "INSERT INTO operation_logs (user_id, action, detail, ip) VALUES (%s,%s,%s,%s)",
            (user_id, action, detail[:500], _client_ip())
        )
    except Exception as e:
        print("[log] 操作日志写入失败:", e)


def _clip_classify(save_path):
    """传统 CLIP 零样本分类，返回 (scene, desc_dict)。"""
    img = Image.open(save_path).convert("RGB")
    img_tensor = preprocess(img).unsqueeze(0).to(device)
    txt_tokens = get_scene_tokens(device)
    img_feat = get_image_feature(model, img_tensor, device)
    txt_feat = model.encode_text(txt_tokens)
    sim = cosine_sim(img_feat, txt_feat)
    scene = classify_scene(sim)
    return scene, {"scene": scene}


@app.route("/")
def index():
    return render_template('index.html')


# ============================================================
# 用户体系：注册 / 登录 / 退出 / 个人中心 / 改密
# ============================================================

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json(force=True)
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if len(username) < 3 or len(password) < 6:
        return jsonify(ok=False, msg="账号至少3位，密码至少6位"), 400

    exist = db.query_one("SELECT id FROM users WHERE username=%s", (username,))
    if exist:
        return jsonify(ok=False, msg="该账号已被注册"), 400

    pwd_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_id = db.insert_get_id(
        "INSERT INTO users (username, password_hash, nickname) VALUES (%s, %s, %s)",
        (username, pwd_hash, username)
    )
    session['user_id'] = new_id
    session['role'] = 'user'
    return jsonify(ok=True, msg="注册成功",
                   user={"id": new_id, "username": username, "role": "user", "nickname": username})


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(force=True)
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    user = db.query_one("SELECT * FROM users WHERE username=%s", (username,))
    ip = _client_ip()

    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        db.execute("INSERT INTO login_logs (user_id, username, ip, success) VALUES (%s,%s,%s,%s)",
                   (user['id'] if user else None, username, ip, 0))
        return jsonify(ok=False, msg="账号或密码错误"), 401

    session['user_id'] = user['id']
    session['role'] = user['role']
    db.execute("UPDATE users SET last_login=%s WHERE id=%s", (datetime.now(), user['id']))
    db.execute("INSERT INTO login_logs (user_id, username, ip, success) VALUES (%s,%s,%s,%s)",
               (user['id'], username, ip, 1))
    return jsonify(ok=True, msg="登录成功",
                   user={"id": user['id'], "username": user['username'],
                         "role": user['role'], "nickname": user['nickname'],
                         "avatar": user['avatar']})


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify(ok=True, msg="已退出登录")


@app.route('/api/me')
def me():
    u = _current_user()
    if not u:
        return jsonify(ok=False, msg="未登录")
    return jsonify(ok=True, user=u)


@app.route('/api/profile', methods=['POST'])
def update_profile():
    u = _current_user()
    if not u:
        return jsonify(ok=False, msg="未登录"), 401
    data = request.get_json(force=True)
    nickname = (data.get('nickname') or '').strip()
    avatar = data.get('avatar') or ''
    db.execute("UPDATE users SET nickname=%s, avatar=%s WHERE id=%s",
               (nickname, avatar, u['id']))
    return jsonify(ok=True, msg="资料已更新")


@app.route('/api/upload-avatar', methods=['POST'])
def upload_avatar():
    """上传用户头像，存到 static/avatars，返回可访问 URL。"""
    u = _current_user()
    if not u:
        return jsonify(ok=False, msg="未登录"), 401
    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify(ok=False, msg="请选择图片"), 400
    import os, uuid
    from config import STATIC_DIR
    avatar_dir = os.path.join(STATIC_DIR, "avatars")
    os.makedirs(avatar_dir, exist_ok=True)
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
        return jsonify(ok=False, msg="仅支持 jpg/png/gif/webp"), 400
    fname = f"avatar_{u['id']}_{uuid.uuid4().hex[:8]}{ext}"
    save_path = os.path.join(avatar_dir, fname)
    file.save(save_path)
    url = f"/static/avatars/{fname}"
    db.execute("UPDATE users SET avatar=%s WHERE id=%s", (url, u['id']))
    log_action(u['id'], 'upload_avatar', url)
    return jsonify(ok=True, url=url, msg="头像已更新")


@app.route('/api/change-password', methods=['POST'])
def change_password():
    u = _current_user()
    if not u:
        return jsonify(ok=False, msg="未登录"), 401
    data = request.get_json(force=True)
    old_pwd = data.get('old_password') or ''
    new_pwd = data.get('new_password') or ''
    if len(new_pwd) < 6:
        return jsonify(ok=False, msg="新密码至少6位"), 400

    full = db.query_one("SELECT password_hash FROM users WHERE id=%s", (u['id'],))
    if not bcrypt.checkpw(old_pwd.encode('utf-8'), full['password_hash'].encode('utf-8')):
        return jsonify(ok=False, msg="原密码错误"), 400

    new_hash = bcrypt.hashpw(new_pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db.execute("UPDATE users SET password_hash=%s WHERE id=%s", (new_hash, u['id']))
    return jsonify(ok=True, msg="密码已修改")


# ============================================================
# 图片识别 + 文案生成
# ============================================================

@app.route('/predict', methods=['POST'])
def predict():
    try:
        file = request.files['file']
        instruction = request.form.get('instruction', '治愈')

        unique_filename = str(uuid.uuid4()) + "_" + secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(save_path)
        img_path = f"/static/uploads/{unique_filename}"

        # CLIP 多模态零样本分类
        img = Image.open(save_path).convert("RGB")
        img_tensor = preprocess(img).unsqueeze(0).to(device)
        txt_tokens = get_scene_tokens(device)
        img_feat = get_image_feature(model, img_tensor, device)
        txt_feat = model.encode_text(txt_tokens)
        sim = cosine_sim(img_feat, txt_feat)
        scene = classify_scene(sim)

        # LLM 基于场景 + 用户要求生成文案
        caption = generate_caption(scene, instruction)

        # 生成记录入库（登录则关联 user_id，未登录存 NULL）
        uid = session.get('user_id')
        record_id = None
        try:
            record_id = db.insert_get_id(
                "INSERT INTO records (user_id, img_path, scene, style, caption) VALUES (%s,%s,%s,%s,%s)",
                (uid, img_path, scene, instruction, caption)
            )
        except Exception as e:
            print("[db] 记录入库失败:", e)

        log_action(uid, 'generate', f"场景={scene}, 风格={instruction}")

        return jsonify(
            scene=scene,
            caption=caption,
            imgPath=img_path,
            recordId=record_id,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(scene="识别失败", caption=str(e)), 500


@app.route('/api/history')
def history():
    """返回当前登录用户的生成记录（最新在前）。未登录返回空列表。"""
    u = _current_user()
    if not u:
        return jsonify(ok=True, list=[])
    rows = db.query(
        "SELECT id, img_path, scene, style, caption, created_at "
        "FROM records WHERE user_id=%s ORDER BY id DESC LIMIT 50",
        (u['id'],)
    )
    # 时间格式化，方便前端显示
    for r in rows:
        r['time'] = r['created_at'].strftime('%Y/%m/%d %H:%M:%S') if r['created_at'] else ''
    return jsonify(ok=True, list=rows)


# ============================================================
# B 内容互动：收藏 / 点赞 / 发布广场 / 评分 / 再编辑
# ============================================================

def _require_user():
    u = _current_user()
    if not u:
        return None
    return u


@app.route('/api/favorite', methods=['POST'])
def toggle_favorite():
    """收藏/取消收藏某条记录。"""
    u = _require_user()
    if not u:
        return jsonify(ok=False, msg="请先登录"), 401
    data = request.get_json(force=True)
    rid = data.get('record_id')
    exist = db.query_one(
        "SELECT id FROM favorites WHERE user_id=%s AND record_id=%s", (u['id'], rid))
    if exist:
        db.execute("DELETE FROM favorites WHERE id=%s", (exist['id'],))
        return jsonify(ok=True, favorited=False, msg="已取消收藏")
    db.execute("INSERT INTO favorites (user_id, record_id) VALUES (%s,%s)", (u['id'], rid))
    return jsonify(ok=True, favorited=True, msg="已收藏")


@app.route('/api/favorites')
def my_favorites():
    """我的收藏列表（join 记录内容）。"""
    u = _require_user()
    if not u:
        return jsonify(ok=False, msg="请先登录"), 401
    rows = db.query(
        "SELECT r.id, r.img_path, r.scene, r.style, r.caption, f.created_at "
        "FROM favorites f JOIN records r ON f.record_id=r.id "
        "WHERE f.user_id=%s ORDER BY f.id DESC LIMIT 50", (u['id'],))
    for r in rows:
        r['time'] = r['created_at'].strftime('%Y/%m/%d %H:%M:%S') if r['created_at'] else ''
    return jsonify(ok=True, list=rows)


@app.route('/api/publish', methods=['POST'])
def toggle_publish():
    """把自己的某条记录发布到广场 / 取消发布。"""
    u = _require_user()
    if not u:
        return jsonify(ok=False, msg="请先登录"), 401
    data = request.get_json(force=True)
    rid = data.get('record_id')
    rec = db.query_one("SELECT user_id, is_public FROM records WHERE id=%s", (rid,))
    if not rec or rec['user_id'] != u['id']:
        return jsonify(ok=False, msg="只能操作自己的记录"), 403
    new_val = 0 if rec['is_public'] else 1
    db.execute("UPDATE records SET is_public=%s WHERE id=%s", (new_val, rid))
    log_action(u['id'], 'publish' if new_val else 'unpublish', f"record_id={rid}")
    return jsonify(ok=True, is_public=new_val,
                   msg="已发布到广场" if new_val else "已从广场下架")


@app.route('/api/like', methods=['POST'])
def toggle_like():
    """广场点赞/取消。"""
    u = _require_user()
    if not u:
        return jsonify(ok=False, msg="请先登录"), 401
    data = request.get_json(force=True)
    rid = data.get('record_id')
    exist = db.query_one(
        "SELECT id FROM likes WHERE user_id=%s AND record_id=%s", (u['id'], rid))
    if exist:
        db.execute("DELETE FROM likes WHERE id=%s", (exist['id'],))
        return jsonify(ok=True, liked=False)
    db.execute("INSERT INTO likes (user_id, record_id) VALUES (%s,%s)", (u['id'], rid))
    return jsonify(ok=True, liked=True)


@app.route('/api/square')
def square():
    """广场：所有公开记录，附带作者、点赞数、评论数、当前用户是否已赞。可按场景筛选。"""
    scene_filter = request.args.get('scene', '')
    where = "WHERE r.is_public=1"
    args = []
    if scene_filter:
        where += " AND r.scene=%s"
        args.append(scene_filter)
    rows = db.query(
        "SELECT r.id, r.img_path, r.scene, r.style, r.caption, r.created_at, r.user_id AS author_id, "
        "u.nickname AS author, "
        "(SELECT COUNT(*) FROM likes l WHERE l.record_id=r.id) AS like_cnt, "
        "(SELECT COUNT(*) FROM favorites f WHERE f.record_id=r.id) AS fav_cnt, "
        "(SELECT COUNT(*) FROM comments c WHERE c.record_id=r.id) AS comment_cnt "
        "FROM records r LEFT JOIN users u ON r.user_id=u.id "
        + where + " ORDER BY r.id DESC LIMIT 100", tuple(args))
    uid = session.get('user_id')
    liked_ids = set()
    fav_ids = set()
    if uid:
        liked_rows = db.query("SELECT record_id FROM likes WHERE user_id=%s", (uid,))
        liked_ids = {x['record_id'] for x in liked_rows}
        fav_rows = db.query("SELECT record_id FROM favorites WHERE user_id=%s", (uid,))
        fav_ids = {x['record_id'] for x in fav_rows}
    for r in rows:
        r['time'] = r['created_at'].strftime('%Y/%m/%d %H:%M:%S') if r['created_at'] else ''
        r['liked'] = r['id'] in liked_ids
        r['favorited'] = r['id'] in fav_ids
    return jsonify(ok=True, list=rows)


@app.route('/api/rating', methods=['POST'])
def rate():
    """对某条记录评分（重复评分覆盖）。"""
    u = _require_user()
    if not u:
        return jsonify(ok=False, msg="请先登录"), 401
    data = request.get_json(force=True)
    rid = data.get('record_id')
    score = int(data.get('score', 5))
    exist = db.query_one(
        "SELECT id FROM ratings WHERE user_id=%s AND record_id=%s", (u['id'], rid))
    if exist:
        db.execute("UPDATE ratings SET score=%s WHERE id=%s", (score, exist['id']))
    else:
        db.execute("INSERT INTO ratings (user_id, record_id, score) VALUES (%s,%s,%s)",
                   (u['id'], rid, score))
    return jsonify(ok=True, msg="已评分", score=score)


@app.route('/api/edit-caption', methods=['POST'])
def edit_caption():
    """再编辑自己的文案。"""
    u = _require_user()
    if not u:
        return jsonify(ok=False, msg="请先登录"), 401
    data = request.get_json(force=True)
    rid = data.get('record_id')
    new_caption = (data.get('caption') or '').strip()
    if not new_caption:
        return jsonify(ok=False, msg="文案不能为空"), 400
    rec = db.query_one("SELECT user_id FROM records WHERE id=%s", (rid,))
    if not rec or rec['user_id'] != u['id']:
        return jsonify(ok=False, msg="只能编辑自己的记录"), 403
    db.execute("UPDATE records SET caption=%s, is_edited=1 WHERE id=%s", (new_caption, rid))
    log_action(u['id'], 'edit_caption', f"record_id={rid}")
    return jsonify(ok=True, msg="文案已更新", caption=new_caption)


@app.route('/api/correct', methods=['POST'])
def correct_scene():
    """人工纠错：用户发现模型识别错了，提交正确场景。"""
    u = _require_user()
    if not u:
        return jsonify(ok=False, msg="请先登录"), 401
    data = request.get_json(force=True)
    rid = data.get('record_id')
    correct = (data.get('correct_scene') or '').strip()
    valid_scenes = ["海边", "山林", "落日", "古镇", "湖泊", "街巷", "草原", "城市天际线"]
    if correct not in valid_scenes:
        return jsonify(ok=False, msg="请选择合法场景"), 400
    rec = db.query_one("SELECT scene FROM records WHERE id=%s", (rid,))
    if not rec:
        return jsonify(ok=False, msg="记录不存在"), 404
    db.execute(
        "INSERT INTO corrections (record_id, user_id, wrong_scene, correct_scene) VALUES (%s,%s,%s,%s)",
        (rid, u['id'], rec['scene'], correct))
    log_action(u['id'], 'correct', f"{rec['scene']} -> {correct}")
    return jsonify(ok=True, msg="已提交纠错，感谢反馈")


@app.route('/api/stats')
def stats():
    """数据统计：规模、场景分布、风格分布、纠错与准确率。"""
    total = db.query_one("SELECT COUNT(*) c FROM records")['c']
    users = db.query_one("SELECT COUNT(*) c FROM users")['c']
    public = db.query_one("SELECT COUNT(*) c FROM records WHERE is_public=1")['c']
    fav_cnt = db.query_one("SELECT COUNT(*) c FROM favorites")['c']
    correct_cnt = db.query_one("SELECT COUNT(*) c FROM corrections")['c']

    # 场景分布
    scene_dist = db.query(
        "SELECT scene, COUNT(*) c FROM records GROUP BY scene ORDER BY c DESC")
    # 风格分布（取出现频次高的）
    style_dist = db.query(
        "SELECT style, COUNT(*) c FROM records GROUP BY style ORDER BY c DESC LIMIT 10")
    # 易混场景：纠错记录中 wrong->correct 分布
    confusion = db.query(
        "SELECT wrong_scene, correct_scene, COUNT(*) c FROM corrections GROUP BY wrong_scene, correct_scene ORDER BY c DESC")

    # 准确率：有纠错的记录数 / 总记录数（粗略，仅作展示）
    accuracy = round((total - correct_cnt) / total * 100, 1) if total else 100.0

    return jsonify(ok=True, data={
        'total': total,
        'users': users,
        'public': public,
        'favorites': fav_cnt,
        'corrections': correct_cnt,
        'accuracy': accuracy,
        'scene_dist': scene_dist,
        'style_dist': style_dist,
        'confusion': confusion,
    })


# ============================================================
# A 管理员后台
# ============================================================

def _require_admin():
    u = _current_user()
    if not u:
        return None, (jsonify(ok=False, msg="请先登录"), 401)
    if u.get('role') != 'admin':
        return None, (jsonify(ok=False, msg="无管理员权限"), 403)
    return u, None


@app.route('/api/admin/users')
def admin_users():
    u, err = _require_admin()
    if err:
        return err
    rows = db.query(
        "SELECT id, username, nickname, role, created_at, "
        "(SELECT COUNT(*) FROM records r WHERE r.user_id=users.id) AS record_cnt "
        "FROM users ORDER BY id ASC")
    for r in rows:
        r['created_at'] = r['created_at'].strftime('%Y-%m-%d') if r['created_at'] else ''
    return jsonify(ok=True, list=rows)


@app.route('/api/admin/records')
def admin_records():
    u, err = _require_admin()
    if err:
        return err
    rows = db.query(
        "SELECT r.id, r.img_path, r.scene, r.style, r.caption, r.is_public, r.created_at, "
        "u.username AS author "
        "FROM records r LEFT JOIN users u ON r.user_id=u.id "
        "ORDER BY r.id DESC LIMIT 200")
    for r in rows:
        r['time'] = r['created_at'].strftime('%Y/%m/%d %H:%M') if r['created_at'] else ''
    return jsonify(ok=True, list=rows)


@app.route('/api/admin/delete-record', methods=['POST'])
def admin_delete_record():
    u, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True)
    rid = data.get('record_id')
    # 级联清理相关互动数据
    for t in ['favorites', 'likes', 'ratings', 'corrections']:
        db.execute(f"DELETE FROM {t} WHERE record_id=%s", (rid,))
    db.execute("DELETE FROM records WHERE id=%s", (rid,))
    log_action(u['id'], 'admin_delete_record', f"record_id={rid}")
    return jsonify(ok=True, msg="记录已删除")


@app.route('/api/admin/delete-user', methods=['POST'])
def admin_delete_user():
    u, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True)
    uid = data.get('user_id')
    if uid == u['id']:
        return jsonify(ok=False, msg="不能删除自己"), 400
    # 级联删除该用户相关数据
    db.execute("DELETE FROM operation_logs WHERE user_id=%s", (uid,))
    db.execute("DELETE FROM login_logs WHERE user_id=%s", (uid,))
    db.execute("DELETE FROM favorites WHERE user_id=%s", (uid,))
    db.execute("DELETE FROM likes WHERE user_id=%s", (uid,))
    db.execute("DELETE FROM ratings WHERE user_id=%s", (uid,))
    db.execute("DELETE FROM records WHERE user_id=%s", (uid,))
    db.execute("DELETE FROM users WHERE id=%s", (uid,))
    log_action(u['id'], 'admin_delete_user', f"deleted_user_id={uid}")
    return jsonify(ok=True, msg="用户已删除")


# ============================================================
# 风景广场社交：评论 / 关注 / 用户主页
# ============================================================

@app.route('/api/comments')
def list_comments():
    """某条记录的评论列表。"""
    rid = request.args.get('record_id')
    rows = db.query(
        "SELECT c.id, c.content, c.created_at, u.nickname AS author "
        "FROM comments c LEFT JOIN users u ON c.user_id=u.id "
        "WHERE c.record_id=%s ORDER BY c.id ASC LIMIT 100", (rid,))
    for r in rows:
        r['time'] = r['created_at'].strftime('%m-%d %H:%M') if r['created_at'] else ''
    return jsonify(ok=True, list=rows)


@app.route('/api/comment', methods=['POST'])
def add_comment():
    u = _require_user()
    if not u:
        return jsonify(ok=False, msg="请先登录"), 401
    data = request.get_json(force=True)
    rid = data.get('record_id')
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify(ok=False, msg="评论不能为空"), 400
    if len(content) > 500:
        return jsonify(ok=False, msg="评论最长500字"), 400
    db.execute(
        "INSERT INTO comments (record_id, user_id, content) VALUES (%s,%s,%s)",
        (rid, u['id'], content))
    log_action(u['id'], 'comment', f"record_id={rid}")
    return jsonify(ok=True, msg="评论成功")


@app.route('/api/follow', methods=['POST'])
def toggle_follow():
    """关注/取关某作者。"""
    u = _require_user()
    if not u:
        return jsonify(ok=False, msg="请先登录"), 401
    data = request.get_json(force=True)
    followee_id = data.get('user_id')
    if not followee_id or int(followee_id) == u['id']:
        return jsonify(ok=False, msg="不能关注自己"), 400
    exist = db.query_one(
        "SELECT id FROM follows WHERE follower_id=%s AND followee_id=%s", (u['id'], followee_id))
    if exist:
        db.execute("DELETE FROM follows WHERE id=%s", (exist['id'],))
        return jsonify(ok=True, following=False, msg="已取关")
    db.execute(
        "INSERT INTO follows (follower_id, followee_id) VALUES (%s,%s)", (u['id'], followee_id))
    log_action(u['id'], 'follow', f"followee={followee_id}")
    return jsonify(ok=True, following=True, msg="已关注")


@app.route('/api/user/<int:uid>')
def user_profile(uid):
    """用户主页：该作者信息 + 其公开分享。"""
    info = db.query_one(
        "SELECT id, username, nickname, created_at FROM users WHERE id=%s", (uid,))
    if not info:
        return jsonify(ok=False, msg="用户不存在"), 404
    info['member_since'] = info['created_at'].strftime('%Y-%m') if info['created_at'] else ''
    shares = db.query(
        "SELECT id, img_path, scene, style, caption, created_at, "
        "(SELECT COUNT(*) FROM likes l WHERE l.record_id=records.id) AS like_cnt "
        "FROM records WHERE user_id=%s AND is_public=1 ORDER BY id DESC LIMIT 100", (uid,))
    for s in shares:
        s['time'] = s['created_at'].strftime('%Y/%m/%d') if s['created_at'] else ''
    fans = db.query_one("SELECT COUNT(*) c FROM follows WHERE followee_id=%s", (uid,))['c']
    following = db.query_one("SELECT COUNT(*) c FROM follows WHERE follower_id=%s", (uid,))['c']
    # 当前登录用户是否已关注该作者
    me_id = session.get('user_id')
    is_following = False
    if me_id:
        is_following = db.query_one(
            "SELECT id FROM follows WHERE follower_id=%s AND followee_id=%s", (me_id, uid)) is not None
    return jsonify(ok=True, info=info, shares=shares, fans=fans, following_cnt=following,
                   is_following=is_following)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
