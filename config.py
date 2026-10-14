import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 三大目录正式启用
DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "model")
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_FOLDER = os.path.join(STATIC_DIR, "uploads")
TEMPLATE_FOLDER = os.path.join(BASE_DIR, "templates")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 模型
CLIP_MODEL_NAME = "ViT-B-32"
MODEL_PATH = os.path.join(MODEL_DIR, "ViT-B-32.pt")

# 场景与风格
SCENE_LABELS = ["海边", "山林", "落日", "古镇", "湖泊", "街巷", "草原", "城市天际线"]
CAPTION_STYLES = ["治愈", "文艺", "伤感"]

# Ollama 本地大模型（文案生成）
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:7b"

# 默认推理模式：clip（CLIP 多模态零样本分类）
DEFAULT_MODE = "clip"

SECRET_KEY = "123456"

# MySQL 数据库配置
MYSQL_HOST = "localhost"
MYSQL_PORT = 3306
MYSQL_USER = "root"
MYSQL_PASSWORD = "xu87365333"
MYSQL_DB = "landscape_db"