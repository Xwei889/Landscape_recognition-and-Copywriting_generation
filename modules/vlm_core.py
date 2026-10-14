"""
VLM 视觉理解模块
调用本地 Ollama 的 qwen2.5vl 视觉大模型，对风景图片做结构化分析。
输出固定 schema 的 JSON，供下游文案生成模块使用。
"""
import base64
import io
import json
import os
import re

import requests
from PIL import Image

from config import OLLAMA_BASE_URL, VLM_MODEL

# 简化、直接的 prompt（小模型对复杂角色扮演指令遵守度低）
VLM_SYSTEM_PROMPT = """你是一个图片描述工具。用户给你一张风景照片，你必须只输出一个 JSON 对象，不要解释，不要前后缀，不要 markdown。

输出格式必须严格如下：
{"scene":"主场景","objects":"主要景物","lighting":"光线时段","color":"主色调","weather":"天气","mood":"氛围词"}

其中：
- scene 只能是：海边、山林、落日、古镇、湖泊、街巷、草原、城市天际线、其他 之一
- 所有值都用中文，简短，只写你在图里真实看到的，不要编造

示例输出：
{"scene":"海边","objects":"海浪,沙滩,礁石","lighting":"傍晚金色晚霞","color":"橘红暖调","weather":"晴朗","mood":"治愈"}
"""

VLM_USER_PROMPT = "描述这张图。"


def _encode_image(image_path: str) -> str:
    """读图、缩放、压缩后 base64 编码（减少视觉 token 和内存占用）。"""
    img = Image.open(image_path).convert("RGB")
    # 最长边缩到 512，大幅减少视觉 token 和内存占用
    max_side = 512
    if max(img.size) > max_side:
        ratio = max_side / max(img.size)
        img = img.resize((int(img.size[0] * ratio), int(img.size[1] * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"VLM 输出中未找到 JSON: {text[:200]}")
    return json.loads(text[start:end + 1])


def _normalize(raw: dict) -> dict:
    """把 VLM 返回的各种 JSON 结构归一化到统一 schema。"""
    # 如果 VLM 套了一层 {code, data:{...}}，剥开 data
    if "data" in raw and isinstance(raw["data"], dict):
        raw = {**raw, **raw["data"]}

    # 字段名映射（VLM 可能用不同 key）
    mapping = {
        "scene": ["scene", "场景", "title"],
        "main_objects": ["objects", "main_objects", "景物", "content"],
        "lighting": ["lighting", "光线"],
        "color_tone": ["color", "color_tone", "色调"],
        "weather": ["weather", "天气"],
        "mood": ["mood", "氛围"],
    }
    out = {}
    for out_key, candidates in mapping.items():
        for k in candidates:
            if k in raw and raw[k]:
                out[out_key] = str(raw[k]).strip()
                break
        out.setdefault(out_key, "")

    # 如果 objects 里有 content 长描述，截断一下
    if len(out.get("main_objects", "")) > 100:
        out["main_objects"] = out["main_objects"][:100]

    return out


def analyze_image(image_path: str) -> dict:
    if not os.path.exists(image_path):
        return _fallback_description("未知图片")

    b64 = _encode_image(image_path)

    payload = {
        "model": VLM_MODEL,
        "messages": [
            {"role": "system", "content": VLM_SYSTEM_PROMPT},
            {"role": "user", "content": VLM_USER_PROMPT, "images": [b64]},
        ],
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 1024},
        "keep_alive": 0,  # 用完立刻卸载，腾内存给 LLM
    }

    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=180,
        )
        resp.raise_for_status()
        content = resp.json()["message"]["content"].strip()
        print(f"[VLM] 原始输出: {content[:300]}")  # 调试日志

        raw = _extract_json(content)
        desc = _normalize(raw)
        if not desc.get("scene"):
            desc["scene"] = "风景"

        # 立刻强制卸载 VLM，腾内存给 LLM（关键：两个 7B 不能同时驻留）
        try:
            requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={"model": VLM_MODEL, "keep_alive": 0},
                timeout=10,
            )
            print(f"[VLM] 已卸载 {VLM_MODEL}")
        except Exception:
            pass

        return desc
    except Exception as e:
        print(f"[VLM] 分析失败：{e}")
        # 失败时也尝试卸载
        try:
            requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={"model": VLM_MODEL, "keep_alive": 0},
                timeout=5,
            )
        except Exception:
            pass
        return _fallback_description("风景")


def _fallback_description(scene: str) -> dict:
    return {
        "scene": scene,
        "main_objects": "",
        "lighting": "",
        "color_tone": "",
        "weather": "",
        "mood": "",
    }


def description_to_text(desc: dict) -> str:
    parts = [f"主场景：{desc.get('scene', '')}"]
    if desc.get("main_objects"):
        parts.append(f"主要景物：{desc['main_objects']}")
    if desc.get("lighting"):
        parts.append(f"光线：{desc['lighting']}")
    if desc.get("color_tone"):
        parts.append(f"色调：{desc['color_tone']}")
    if desc.get("weather"):
        parts.append(f"天气：{desc['weather']}")
    if desc.get("mood"):
        parts.append(f"氛围：{desc['mood']}")
    return "；".join(p for p in parts if p)
