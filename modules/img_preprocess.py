from PIL import Image
import io
import torch
from torchvision import transforms
from config import IMAGE_SIZE

# 图像预处理流水线
preprocess = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.48145466, 0.4578275, 0.40821073],
        std=[0.26862954, 0.26130258, 0.27577711]
    )
])

def preprocess_image(file_bytes):
    """
    读取图片字节流，预处理成模型可输入的张量
    """
    img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    img_tensor = preprocess(img).unsqueeze(0)
    return img_tensor