import clip
from config import SCENE_LABELS

def get_scene_tokens(device):
    # 英文描述，给CLIP识别用
    texts = [
        "a photo of seaside scenery",
        "a photo of mountain forest scenery",
        "a photo of sunset scenery",
        "a photo of ancient town scenery",
        "a photo of lake scenery",
        "a photo of street alley scenery",
        "a photo of grassland scenery",
        "a photo of city skyline scenery"
    ]
    return clip.tokenize(texts).to(device)