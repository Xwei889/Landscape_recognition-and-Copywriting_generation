from flask import Flask, render_template, request, jsonify
import os
from PIL import Image
from werkzeug.utils import secure_filename
import uuid

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

# CLIP 模型（启动时加载一次）
from modules.clip_core import load_clip_model, get_image_feature, cosine_sim
from modules.scene_classify import classify_scene
from modules.text_preprocess import get_scene_tokens
model, preprocess, device = load_clip_model()

# LLM 文案生成（通过 Ollama HTTP 调用）
from modules.caption_lib import generate_caption


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

        return jsonify(
            scene=scene,
            caption=caption,
            imgPath=img_path,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(scene="识别失败", caption=str(e)), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
