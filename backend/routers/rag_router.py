"""RAG 管理路由 — 知识库构建、状态查询、连接测试"""

from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from schemas import APIResponse

router = APIRouter()


@router.post("/build", response_model=APIResponse)
async def build_knowledge_base(current_user: dict = Depends(get_current_user)):
    """触发知识库构建（全量）

    重新加载所有文档（PDF/Markdown/QA），向量化后写入 ChromaDB。
    耗时取决于文档数量，通常 3-10 分钟。
    """
    try:
        from services.embedding_service import get_embedding_backend, test_dashscope_connection
        from services.rag_service import RAGService
        from services.document_loader import load_all_documents

        # 获取用户配置的嵌入服务
        # 先尝试 dashscope，如果用户没有配置则用 bge local
        from database import get_db
        conn = get_db()
        row = conn.execute(
            "SELECT embedding_provider, embedding_api_key, embedding_model FROM user_llm_config WHERE user_id = ?",
            (current_user["id"],)
        ).fetchone()
        conn.close()

        provider = "dashscope"
        api_key = ""
        model = "text-embedding-v3"

        if row:
            provider = row["embedding_provider"] or "dashscope"
            api_key = row["embedding_api_key"] or ""
            model = row["embedding_model"] or "text-embedding-v3"

        if provider == "dashscope" and not api_key:
            raise HTTPException(
                status_code=400,
                detail="请在「个人中心 → Embedding 配置」中设置阿里云 DashScope API Key"
            )

        # 加载文档
        import os
        chunks = load_all_documents(
            pdf_dir=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "pdf"),
            materials_dir=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "learning_materials"),
            dataset_dir=os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "dataset"),
            index_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "learning_materials", "index.json"),
        )

        if not chunks:
            return APIResponse(data={"error": "未找到任何文档", "total": 0, "new": 0})

        # 构建向量库
        backend = get_embedding_backend(provider=provider, api_key=api_key, model=model, force_reload=True)
        rag = RAGService(backend=backend)
        result = rag.rebuild(chunks)

        return APIResponse(data={
            **result,
            "collection": rag.collection_name,
            "backend": backend.NAME,
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"知识库构建失败: {str(e)}")


@router.get("/status", response_model=APIResponse)
async def get_rag_status(current_user: dict = Depends(get_current_user)):
    """获取知识库状态"""
    try:
        from services.rag_service import get_rag_service

        # 使用默认配置尝试获取状态（不需要用户的 API key）
        try:
            rag = get_rag_service(provider="dashscope", api_key="dummy")
            status = rag.get_status()
        except Exception:
            # 如果 dashscope 不可用，尝试 bge
            from services.rag_service import reset_rag_service
            reset_rag_service()
            rag = get_rag_service(provider="bge")
            status = rag.get_status()

        return APIResponse(data=status)

    except Exception as e:
        return APIResponse(data={"error": str(e), "total_chunks": 0})


@router.post("/reindex", response_model=APIResponse)
async def reindex_knowledge_base(current_user: dict = Depends(get_current_user)):
    """清空并重建知识库"""
    try:
        from services.rag_service import reset_rag_service
        reset_rag_service()
        # 调用 build 逻辑
        return await build_knowledge_base(current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重建失败: {str(e)}")


@router.get("/search", response_model=APIResponse)
async def search_rag(
    q: str = "",
    top_k: int = 5,
    current_user: dict = Depends(get_current_user),
):
    """测试检索（调试用）"""
    if not q:
        return APIResponse(data={"results": [], "query": ""})

    try:
        from services.embedding_service import get_embedding_backend
        from services.rag_service import RAGService

        # 尝试获取用户配置
        from database import get_db
        conn = get_db()
        row = conn.execute(
            "SELECT embedding_provider, embedding_api_key, embedding_model FROM user_llm_config WHERE user_id = ?",
            (current_user["id"],)
        ).fetchone()
        conn.close()

        provider = "dashscope"
        api_key = ""
        model = "text-embedding-v3"

        if row and row["embedding_api_key"]:
            provider = row["embedding_provider"] or "dashscope"
            api_key = row["embedding_api_key"]
            model = row["embedding_model"] or "text-embedding-v3"
        else:
            provider = "bge"

        backend = get_embedding_backend(provider=provider, api_key=api_key, model=model)
        rag = RAGService(backend=backend)
        results = rag.retrieve(q, top_k=top_k)
        sources = rag.get_sources(results)

        return APIResponse(data={
            "query": q,
            "results_count": len(results),
            "sources": sources,
            "results": [
                {
                    "id": r["id"],
                    "text": r["text"][:300],
                    "score": r["score"],
                    "source": r["source"],
                    "metadata": r.get("metadata", {}),
                }
                for r in results
            ],
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")


@router.post("/test-connection", response_model=APIResponse)
async def test_embedding_connection(current_user: dict = Depends(get_current_user)):
    """测试 Embedding API 连通性"""
    try:
        from database import get_db
        conn = get_db()
        row = conn.execute(
            "SELECT embedding_provider, embedding_api_key, embedding_model FROM user_llm_config WHERE user_id = ?",
            (current_user["id"],)
        ).fetchone()
        conn.close()

        if not row or not row["embedding_api_key"]:
            raise HTTPException(status_code=400, detail="请先配置 Embedding API Key")

        from services.embedding_service import test_dashscope_connection
        result = test_dashscope_connection(
            api_key=row["embedding_api_key"],
            model=row["embedding_model"] or "text-embedding-v3",
        )

        return APIResponse(data=result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")
