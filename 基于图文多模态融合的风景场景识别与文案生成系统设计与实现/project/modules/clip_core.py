import torch
import clip
from config import MODEL_PATH

def load_clip_model():
    device = "cpu"
    model, preprocess = clip.load(MODEL_PATH, device=device, download_root=None)
    return model, preprocess, device

def get_image_feature(model, image_tensor, device):
    with torch.no_grad():
        return model.encode_image(image_tensor.to(device))

def get_text_feature(model, text_tokens, device):
    with torch.no_grad():
        return model.encode_text(text_tokens.to(device))

def cosine_sim(img_feat, txt_feat):
    return (100.0 * img_feat @ txt_feat.T).softmax(dim=-1)