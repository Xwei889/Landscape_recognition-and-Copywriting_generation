import json
import random
import os
from config import DATA_DIR

def load_caption_lib():
    path = os.path.join(DATA_DIR, "caption_lib.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_caption(scene, style="治愈"):
    lib = load_caption_lib()
    scene_data = lib.get(scene, {})
    cap_list = scene_data.get(style, ["人间烟火，皆是温柔"])
    return random.choice(cap_list)