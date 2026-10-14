"""
文案生成模块
接收 CLIP 分类出的场景标签，结合用户指定风格，调用本地 qwen2.5:7b 写文案。
"""
import json
import os
import random

import requests

from config import OLLAMA_BASE_URL, OLLAMA_MODEL, DATA_DIR

# 本地文案库路径（大模型不可用时兜底）
CAPTION_LIB_PATH = os.path.join(DATA_DIR, "caption_lib.json")


def generate_caption(scene, instruction):
    """
    根据场景标签和用户要求生成文案。
    :param scene: CLIP 分类出的场景名（海边/山林/落日/古镇/湖泊/街巷/草原/城市天际线）
    :param instruction: 用户对文案的要求（风格 + 自定义指令，如"治愈，短一点，适合小红书"）
    """
    data = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是一位高级朋友圈文案师，擅长氛围感、高级、简短、有画面感的文字。"
            },
            {
                "role": "user",
                "content": f"""
根据下面的【场景】和【文案要求】，创作一句适合发朋友圈的短文案。

【场景】{scene}
【文案要求】{instruction}

要求：
1. 紧扣场景意象，呼应文案要求里的每一个细节
2. 适合朋友圈、小红书，有留白感
3. 每次创作都要独特，避免重复句式
4. 只用比喻、拟人、留白等手法，不要堆砌形容词
5. 只输出文案本身，不要解释，不要前后标点
"""
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0.9,
            "top_p": 0.95,
        },
        "keep_alive": 0
    }

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=data,
            timeout=180
        )
        if response.status_code == 200:
            caption = response.json()["message"]["content"].strip()
            if caption:
                return caption
    except Exception as e:
        print(f"[Caption] 大模型调用失败：{e}")

    return _fallback_caption(scene, instruction)


def _fallback_caption(scene, instruction):
    """从本地文案库随机抽取兜底。"""
    style = instruction if instruction in ['治愈', '文艺', '伤感'] else '治愈'
    try:
        with open(CAPTION_LIB_PATH, "r", encoding="utf-8") as f:
            lib = json.load(f)
        captions = lib.get(scene, {}).get(style)
        if captions:
            return random.choice(captions)
    except Exception as e:
        print(f"[Caption] 本地文案库读取失败：{e}")

    return f"{scene}的风，带着{instruction}的温柔"
