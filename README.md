# AI智能体学科学习平台 Demo

## 项目简介
专注于AI智能体单一学科的个性化、伴随式、智能化学习平台。覆盖课前预习、课中理解、课后巩固、复盘提升全学习链路。

## 五大核心模块
1. **智能学情诊断** — AI动态出题，精准定位知识盲区
2. **专业知识答疑** — 分层讲解，代码/算法/理论全覆盖
3. **伴随式学习** — 学习路径规划 + 每日任务 + 错题归因
4. **学情复盘** — 多维度数据统计 + 能力成长可视化
5. **资源推送** — 基于学情的个性化资源推荐

## 技术栈
- 前端：Vue3 + Vite + Element Plus + ECharts
- 后端：Python FastAPI + SQLite
- AI：DeepSeek API

## 快速启动

### 方式一：Docker 一键启动 (推荐)

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看运行状态
docker-compose ps

# 停止服务
docker-compose down
```

### 方式二：一键启动 (Windows)
双击 `start.bat`

### 方式三：分别启动

1. 启动后端：
```bash
cd backend
pip install -r requirements.txt
python main.py
```

2. 启动前端：
```bash
cd frontend
npm install
npm run dev
```

3. 访问：
- 前端：http://localhost:5173
- API文档：http://localhost:8000/docs
- Demo账号：demo / demo123

## 项目结构
```
├── backend/           # Python FastAPI 后端
│   ├── main.py        # 入口
│   ├── routers/       # API路由
│   ├── services/      # 业务逻辑
│   └── data/          # 静态数据
├── frontend/          # Vue3 前端
│   └── src/
│       ├── views/     # 页面组件
│       ├── components/# 通用组件
│       ├── stores/    # Pinia状态
│       ├── api/       # API封装
│       └── router/    # 路由配置
└── start.bat          # 一键启动
```
