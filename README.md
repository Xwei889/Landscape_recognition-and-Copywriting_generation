# 风景场景识别与文案生成系统

## 项目简介
基于 Flask + Vue3 的图文多模态风景场景识别与智能文案生成系统。上传风景图片后，由 CLIP 完成场景识别，再调用本地部署的大语言模型 Qwen2.5-7B（Ollama），结合用户选择的风格或自定义要求生成文案。前端采用 Neo-Brutalist（新野兽派）设计风格，左侧常驻最近生成记录。

## 核心功能
- **图像上传预览**：支持本地风景图片上传与实时预览
- **CLIP 场景识别**：基于 OpenAI CLIP ViT-B/32 零样本分类，识别多类风景场景
- **LLM 文案生成**：通过 Ollama 调用本地 Qwen2.5-7B，生成场景化文案
- **七种推荐风格**：治愈、文艺、伤感、俏皮、复古、氛围感、极简，一键选用
- **自定义要求**：支持输入个性化要求（如"短一点、带点幽默"）
- **历史记录侧边栏**：左侧常驻最近生成记录，点击可回看
- **一键复制**：生成文案快速复制分享
- **本地离线运行**：模型全部本地部署，无需联网

## 技术架构
| 模块 | 技术 |
|------|------|
| 视觉识别 | OpenAI CLIP ViT-B/32（PyTorch） |
| 文案生成 | Ollama + Qwen2.5-7B |
| 后端 | Flask + Python |
| 前端 | Vue 3 + Neo-Brutalist 设计 |

## 环境要求
- Python 3.10+
- Flask、PyTorch、Pillow、NumPy
- Ollama（并拉取 qwen2.5:7b 模型）
- CLIP 模型文件 `ViT-B-32.pt`

## 快速开始
1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 模型准备
- 下载 CLIP 模型 `ViT-B-32.pt`，放入 `model/` 目录
- 安装 Ollama 并执行 `ollama pull qwen2.5:7b`

3. 启动服务
```bash
python -m modules.flask_api
```

4. 浏览器访问
```
http://127.0.0.1:5000
```

## 目录结构
```
├── config.py              # 系统配置
├── modules/
│   ├── flask_api.py       # Flask 接口入口
│   ├── clip_core.py       # CLIP 特征提取
│   ├── scene_classify.py  # 场景分类
│   ├── text_preprocess.py # 场景文本处理
│   ├── caption_lib.py     # LLM 文案生成
│   └── vlm_core.py        # VLM 模块（已弃用，保留）
├── templates/
│   └── index.html         # 前端页面
├── static/
│   ├── css/style.css      # 新野兽派样式
│   ├── js/app.js          # Vue 交互逻辑
│   └── uploads/           # 上传图片（不入库）
├── model/                 # 模型目录（大文件不入库）
└── README.md
```

## 使用说明
1. 启动服务后进入首页
2. 上传风景图片
3. 点击推荐风格标签，或在自定义框输入要求
4. 点击"上传并生成文案"，右侧显示识别场景与生成文案
5. 点击历史记录可回看之前的结果
