# CLAUDE.md

## 项目概述
AI智能体学科学习平台 — 专注于AI智能体单一学科的个性化、伴随式、智能化学习平台。

## 技术栈
- 前端：Vue3 + Vite + Element Plus + ECharts（端口 80 via Docker / 5173 本地开发）
- 后端：Python FastAPI + SQLite（端口 8000 via Docker / 8000 本地开发）
- AI：DeepSeek API
- 容器化：Docker Compose

## ⚡ 代码修改后自动部署（必须执行）

**每次修改代码后，必须自动执行以下命令让用户看到效果：**
```bash
docker compose up -d --build
```
- 原因：Docker 前端是 `npm run build` → nginx 静态构建，后端是 Python 源码复制。源码修改必须重建镜像才能生效。
- 用户访问 `http://localhost:80` 看到的是 Docker 版本的代码，不是本地 dev server。

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
| 本地 | `BAAI/bge-large-zh-v1.5` | 1024 | 本地开发默认（无需 API Key） |
| 云端 | 阿里云 DashScope `text-embedding-v3` | 1024 | 生产环境（需用户配置 API Key） |

- **本地开发默认使用 BGE**，无需额外配置即可使用 RAG
- BGE 模型已预下载到 `backend/data/hub/`（~1.3GB），加载后 GPU 占用 ~1.3GB
- 用户可在「个人中心 → AI大模型配置」中填入 DashScope text-embedding-v3 的 API Key 切换到云端嵌入
- HuggingFace 下载使用镜像：`os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'`

### BGE 本地模型
- 模型路径：`backend/data/hub/models--BAAI--bge-large-zh-v1.5/snapshots/79e7739b6ab944e86d6171e44d24c997fc1e0116/`
- 文本截断上限：2400 字符（BGE max_seq_length=512 tokens）
- 批大小：16（RTX 5060 安全值）

### 当前向量库状态
- 集合：`rag_docs_cached-bge-large-zh-v1.5`（BGE 本地）/ `rag_docs_cached-dashscope-text-embedding-v3`（DashScope 历史）
- 存储：`backend/data/chroma_db/`
- 总计 4887 个文档块：PDF 2402 + Markdown 1885 + Q&A 600

### 虚拟环境
- 路径：`backend/.venv/`（Python 3.11.6）
- 核心 RAG 依赖：`chromadb`, `dashscope`, `sentence-transformers`, `torch`（CUDA 13.2）
- 所有 Python 操作必须在激活虚拟环境后执行

### RAG 一键构建
```bash
# 激活 venv
source backend/.venv/Scripts/activate

# 本地 BGE 模式（默认，推荐）
python backend/rag_builder.py --provider bge

# DashScope 云端模式（需用户自行申请 API Key）
python backend/rag_builder.py --api-key <你的DashScope_API_Key>
```
构建后：
- QA 页面提问自动触发 RAG 检索（前提：用户已在个人中心配置嵌入 API Key）
- 未配置时 QA 正常回答，但无知识库增强，并提示用户配置 text-embedding-v3 API Key
- 回答下方展示 📚 参考来源（PDF 页码 / Markdown 章节 / 题库知识点）
- API: `GET /api/rag/status`, `POST /api/rag/search?q=xxx`

### ⚠️ API Key 使用规则（极其重要 — 违反将导致 Key 泄露和账单损失）

**🚫 禁止事项：**
- **绝对禁止将任何真实 API Key 直接写入代码文件**（包括 .py / .js / .vue / .json / .yml / .env）
- 绝不使用硬编码的默认 Key 来兜底——未配置 = 不可用，清晰提示即可
- 测试用的 Key 只能通过浏览器 UI 输入（Playwright），不能写入任何源代码

**✅ 正确做法：**
- 所有 API Key 必须由用户通过前端界面自行输入配置
- 未配置 → 功能不可用 → 显示明确指引（如「请在个人中心配置 xxx API Key」）
- LLM 对话 Key：`个人中心 → DeepSeek 快速配置` 中填写
- 嵌入 Key：`个人中心 → 知识库嵌入 API Key 快速配置` 中填写 DashScope text-embedding-v3
- 本地测试：通过 Playwright 在浏览器中输入 Key，或使用环境变量（不提交）

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
- Docker 构建镜像体积大（含 Python 依赖），修改代码后必须 rebuild
