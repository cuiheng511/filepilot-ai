# FilePilot AI

🚀 智能文件管理工具 — 基于 AI 的文件扫描、检索、去重与自动归类。

## ✨ 功能特性

- **📂 文件扫描** — 高效扫描指定目录，支持递归遍历
- **🔍 全文检索** — 基于 Whoosh 引擎的快速索引和搜索
- **🔗 重复文件检测** — 智能识别重复文件（支持 MD5/SHA1 对比）
- **📁 自动归类** — AI 驱动的文件自动分类整理
- **🖼️ 多媒体提取** — 支持图片 EXIF、PDF 元数据、Markdown 内容提取
- **🧠 AI 双引擎** — 支持本地 Ollama 模型和云端 OpenAI API
- **🎨 图形界面** — 基于 PySide6 的友好桌面 UI

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| 界面 | PySide6 (Qt6) |
| 搜索引擎 | Whoosh |
| AI 本地引擎 | Ollama |
| AI 云端引擎 | OpenAI API |
| 文件哈希 | hashlib (MD5, SHA1) |

## 📦 安装

### 前置条件

- Python 3.11+
- pip

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/cuiheng511/filepilot-ai.git
cd filepilot-ai

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python -m filepilot.main
```

## 🚀 使用指南

### 启动应用

```bash
python -m filepilot.main
```

### 配置 AI

在应用菜单中打开 **设置**，选择：

- **本地模式 (Ollama)** — 使用本地 LLM 模型（如 `qwen2.5:7b`）
- **云端模式 (OpenAI API)** — 配置 API Key 使用云端模型

### 主要功能

1. **索引文件** — 选择目录，点击"开始索引"
2. **搜索文件** — 输入关键词，快速检索文件
3. **查找重复** — 扫描并列出重复文件
4. **自动归类** — 选择目录，AI 自动整理文件结构

## 📁 项目结构

```
filepilot-ai/
├── filepilot/
│   ├── ai/          # AI 引擎（本地 + 云端）
│   ├── core/        # 核心功能（扫描、索引、去重、归类）
│   ├── extractors/  # 文件提取器（代码、图片、PDF、Markdown）
│   ├── ui/          # 图形界面
│   └── utils/       # 工具函数
├── tests/           # 单元测试
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开一个 Pull Request

## 📄 许可证

本项目基于 MIT 许可证开源 — 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [PySide6](https://pypi.org/project/PySide6/) — Qt for Python
- [Whoosh](https://whoosh.readthedocs.io/) — 全文搜索引擎
- [Ollama](https://ollama.ai/) — 本地 LLM 运行时
- [OpenAI](https://openai.com/) — 云端 AI API
