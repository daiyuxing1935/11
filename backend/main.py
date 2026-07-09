"""FastAPI应用入口"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
import os

# 创建应用
app = FastAPI(
    title="AI智能体学科学习平台",
    description="个性化、伴随式、智能化的AI智能体学科学习平台API",
    version="1.0.0"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:80",
        "http://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化数据库
init_db()

# 注册路由
from routers import auth_router, diagnosis_router, qa_router, learning_router, analytics_router, resource_router, knowledge_router, llm_config_router, image_router

app.include_router(auth_router.router, prefix="/api/auth", tags=["认证"])
app.include_router(diagnosis_router.router, prefix="/api/diagnosis", tags=["学情诊断"])
app.include_router(qa_router.router, prefix="/api/qa", tags=["智能答疑"])
app.include_router(learning_router.router, prefix="/api/learning", tags=["伴随学习"])
app.include_router(analytics_router.router, prefix="/api/analytics", tags=["学情复盘"])
app.include_router(resource_router.router, prefix="/api/resources", tags=["资源推送"])
app.include_router(knowledge_router.router, prefix="/api/knowledge", tags=["知识点"])
app.include_router(llm_config_router.router, prefix="/api/llm-config", tags=["LLM配置"])
app.include_router(image_router.router, prefix="/api/images", tags=["图片生成"])


@app.get("/")
def root():
    return {"message": "AI智能体学科学习平台 API", "version": "1.0.0", "status": "running"}

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

@app.get("/api/debug/routes")
def debug_routes():
    """调试：列出所有已注册路由"""
    routes = []
    for r in app.router.routes:
        if hasattr(r, 'methods') and hasattr(r, 'path'):
            routes.append(f"{list(r.methods)} {r.path}")
        elif hasattr(r, 'path'):
            routes.append(f"[include] {r.path}")
    return {"routes": routes}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
