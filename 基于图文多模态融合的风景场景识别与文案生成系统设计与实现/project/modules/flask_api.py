from flask import Flask, render_template, request, jsonify
import os
from PIL import Image
from io import BytesIO

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"))

app.secret_key = "123456"
from config import UPLOAD_FOLDER
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

from modules.clip_core import load_clip_model, get_image_feature, cosine_sim
from modules.scene_classify import classify_scene
from modules.caption_lib import generate_caption
from modules.text_preprocess import get_scene_tokens

model, preprocess, device = load_clip_model()

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/predict', methods=['POST'])
def predict():
    try:
        file = request.files['file']
        style = request.form.get('style', '治愈')

        # 保存图片
        path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(path)

        # 重置指针，读取并转换为 PIL 图像
        file.seek(0)
        img = Image.open(BytesIO(file.read())).convert("RGB")
        img_tensor = preprocess(img).unsqueeze(0).to(device)

        # 场景识别
        txt_tokens = get_scene_tokens(device)
        img_feat = get_image_feature(model, img_tensor, device)
        txt_feat = model.encode_text(txt_tokens)
        sim = cosine_sim(img_feat, txt_feat)
        scene = classify_scene(sim)
        caption = generate_caption(scene, style)

        return jsonify(scene=scene, caption=caption)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(scene="识别失败", caption=str(e)), 500