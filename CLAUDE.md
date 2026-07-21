# CLAUDE.md

## 项目概述
AI智能体学科学习平台 — 专注于AI智能体单一学科的个性化、伴随式、智能化学习平台。

## 技术栈
- 前端：Vue3 + Vite + Element Plus + ECharts（端口 80 via Docker / 5173 本地开发）
- 后端：Python FastAPI + SQLite（端口 8000 via Docker / 8000 本地开发）
- AI：DeepSeek API
- 容器化：Docker Compose

## 启动方式（必须优先使用 Docker）

### 方式一：Docker 一键启动（推荐，始终优先使用）
```bash
docker compose up -d --build
```
- 前端: http://localhost:80
- 后端: http://localhost:8001 （注意 Docker 映射到 8001）
- API 文档: http://localhost:8001/docs

### 方式二：本地开发（仅在 Docker 不可用时使用）

**激活虚拟环境（必须）：**
```bash
# Windows Git Bash:
source backend/.venv/Scripts/activate
# 或 Windows CMD:
backend\.venv\Scripts\activate.bat

# 安装依赖：
pip install -r backend/requirements.txt

# 启动后端：
cd backend && python main.py
```
前端：
```bash
cd frontend && npm install && npm run dev
```

## RAG 知识库引擎

### 嵌入模型（双后端）

| 后端 | 模型 | 维度 | 使用场景 |
|------|------|:---:|------|
| 本地 | `BAAI/bge-large-zh-v1.5` | 1024 | Docker 环境 / 离线开发 |
| 云端 | 阿里云 DashScope `text-embedding-v3` | 1024 | 生产环境（需用户配置 API Key） |

- **用户必须配置 Embedding API 才能使用 RAG**，否则系统提示配置
- 本地模型约 1.3GB，需 8GB+ 显存（RTX 5060 可运行）
- HuggingFace 下载使用镜像：`os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'`
- API Key（测试用）：`sk-c32a6fd48bb048cc93963cad70806dbf`

### 虚拟环境
- 路径：`backend/.venv/`（Python 3.11.6）
- 核心 RAG 依赖：`chromadb`, `dashscope`, `sentence-transformers`
- 所有 Python 操作必须在激活虚拟环境后执行

### RAG 一键构建
```bash
# 激活 venv
source backend/.venv/Scripts/activate

# 全量构建（DashScope 云端，推荐）
python backend/rag_builder.py --api-key sk-c32a6fd48bb048cc93963cad70806dbf

# 本地模式（BGE 模型，首次需下载 ~1.3GB）
python backend/rag_builder.py --provider bge
```
构建后：
- QA 页面提问自动触发 RAG 检索
- 回答下方展示 📚 参考来源（PDF 页码 / Markdown 章节）
- API: `GET /api/rag/status`, `POST /api/rag/search?q=xxx`

### RAG 数据源
| 数据源 | 数量 | 路径 |
|--------|:---:|------|
| AI Agent 中文教材 PDF | 7 本 | `pdf/` |
| Markdown 学习材料 | 81 篇 | `learning_materials/` |
| Q&A 题库 | ~600 条 | `backend/data/dataset/` |

### 参考项目
- SuperMew（agentic RAG）：`F:/code/MyPython/SuperMew-main/`
  - 三层分块 + 自动合并、混合检索 + RRF 融合、LangGraph agentic RAG pipeline
  - 查询扩展（Step-back + HyDE）、Jina Reranker 精排

## 重要注意事项
- `backend/docker-entrypoint.sh` 必须是 **LF** 行尾符（不是 CRLF），否则容器启动报 `Illegal option -`
- Demo 账号：`demo` / `demo123`
- Docker Compose 将后端端口映射为 `127.0.0.1:8001:8000`
