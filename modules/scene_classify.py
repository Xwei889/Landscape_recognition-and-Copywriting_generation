from config import SCENE_LABELS

def classify_scene(similarity):
    idx = similarity.argmax().item()
    return SCENE_LABELS[idx]