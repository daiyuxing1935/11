"""RAG 编排服务 — ChromaDB 向量存储 + 混合检索 + 上下文格式化

核心流程:
1. 文档块 → Embedding → ChromaDB 存储
2. Query → Embedding → 语义检索 + 关键词匹配 → RRF 融合 → 上下文注入
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from .embedding_service import EmbeddingBackend, get_embedding_backend, reset_embedding_backend
from .document_loader import DocumentChunk, load_all_documents

logger = logging.getLogger(__name__)

# ============================================================
# 配置常量
# ============================================================

DEFAULT_CHROMA_PATH = "backend/data/chroma_db"
DEFAULT_TOP_K = 5
CANDIDATE_MULTIPLIER = 3  # 候选文档倍率（语义检索取 top_k * 3，融合后取 top_k）

# RAG Prompt 模板
RAG_CONTEXT_TEMPLATE = """【知识库参考资料】
以下是平台知识库中与本问题最相关的内容，请基于这些资料回答用户问题。
{chunks}

【回答要求】
1. 优先使用知识库中的权威内容，用自己的话重新组织表述
2. 在引用知识库内容时，标注来源编号（如 [1]、[2]）
3. 如果知识库内容不足以完全回答问题，结合你自己的知识补充说明
4. 保持回答结构清晰、语言通俗，适合大学生阅读"""

RAG_SYSTEM_SUPPLEMENT = """你正在使用平台知识库的权威资料辅助回答。请以知识库内容为准，如知识库不完整再结合你的知识补充。"""


# ============================================================
# RAG 服务
# ============================================================

class RAGService:
    """RAG 编排服务"""

    def __init__(self, backend: EmbeddingBackend, chroma_path: str = DEFAULT_CHROMA_PATH):
        self.backend = backend
        self.chroma_path = Path(chroma_path)
        self.chroma_path.mkdir(parents=True, exist_ok=True)

        # 延迟初始化 ChromaDB（避免启动时的导入开销）
        self._client = None
        self._collection = None
        self.collection_name = f"rag_docs_{backend.NAME}"

    @property
    def client(self):
        if self._client is None:
            import chromadb
            self._client = chromadb.PersistentClient(
                path=str(self.chroma_path),
                settings=chromadb.Settings(anonymized_telemetry=False),
            )
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    # ============================================================
    # 文档入库
    # ============================================================

    def ingest(
        self,
        chunks: List[DocumentChunk],
        batch_size: int = 50,
        progress_callback=None,
    ) -> dict:
        """批量向量化并写入 ChromaDB

        Args:
            chunks: 文档块列表
            batch_size: 批大小
            progress_callback: 进度回调 (current, total) -> None

        Returns:
            {"total": int, "new": int, "skipped": int, "errors": int}
        """
        total = len(chunks)
        new_count = 0
        skip_count = 0
        error_count = 0

        # 获取已有文档 ID 集合（去重）
        existing_ids = set()
        try:
            existing = self.collection.get()
            if existing and existing.get("ids"):
                existing_ids = set(existing["ids"])
        except Exception:
            pass  # 空集合

        logger.info(f"开始入库 {total} 个文档块（已有 {len(existing_ids)} 个）...")

        batch_seen = set()  # 批内去重

        for i in range(0, total, batch_size):
            batch = chunks[i:i + batch_size]
            new_batch = []
            new_texts = []

            for chunk in batch:
                doc_id = f"{chunk.source_type}:{chunk.doc_id}"
                if doc_id in existing_ids or doc_id in batch_seen:
                    skip_count += 1
                    continue
                batch_seen.add(doc_id)
                new_batch.append(chunk)
                new_texts.append(chunk.text)

            if not new_texts:
                if progress_callback:
                    progress_callback(min(i + batch_size, total), total)
                continue

            try:
                # 嵌入
                embeddings = self.backend.embed(new_texts)
                ids = [f"{c.source_type}:{c.doc_id}" for c in new_batch]
                metadatas = [
                    {
                        "source_type": c.source_type,
                        "source_path": c.source_path,
                        "title": c.title or "",
                        "module": c.module or "",
                        "page": c.page or 0,
                        "section": c.section or "",
                        "source_label": c.source_label,
                    }
                    for c in new_batch
                ]

                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=new_texts,
                    metadatas=metadatas,
                )
                new_count += len(new_batch)

            except Exception as e:
                logger.error(f"入库批次 [{i}:{i+batch_size}] 失败: {e}")
                error_count += len(new_batch)

            if progress_callback:
                progress_callback(min(i + batch_size, total), total)

        logger.info(f"入库完成: 新增 {new_count}, 跳过 {skip_count}, 错误 {error_count}")
        return {"total": total, "new": new_count, "skipped": skip_count, "errors": error_count}

    # ============================================================
    # 检索
    # ============================================================

    def retrieve(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
    ) -> List[dict]:
        """混合检索主入口

        Returns:
            [{text, metadata, score}, ...]  按相关度降序
        """
        # 1. 语义检索（dense）
        dense_results = self._dense_retrieve(query, top_k * CANDIDATE_MULTIPLIER)

        # 2. 关键词匹配（keyword）
        keyword_results = self._keyword_retrieve(query, top_k * CANDIDATE_MULTIPLIER)

        # 3. RRF 融合
        merged = self._rrf_fusion(dense_results, keyword_results, top_k)

        return merged

    def _dense_retrieve(self, query: str, top_k: int) -> List[dict]:
        """语义向量检索"""
        try:
            query_emb = self.backend.embed_single(query)
            results = self.collection.query(
                query_embeddings=[query_emb],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )

            chunks = []
            if results and results.get("ids") and results["ids"][0]:
                ids = results["ids"][0]
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                dists = results.get("distances", [[]])[0]

                for i, doc_id in enumerate(ids):
                    # cosine distance → similarity score
                    distance = dists[i] if i < len(dists) else 0
                    score = max(0.0, 1.0 - distance)

                    chunks.append({
                        "id": doc_id,
                        "text": docs[i] if i < len(docs) else "",
                        "metadata": metas[i] if i < len(metas) else {},
                        "score": round(score, 4),
                        "source": "dense",
                    })

            return sorted(chunks, key=lambda x: x["score"], reverse=True)

        except Exception as e:
            logger.warning(f"Dense retrieval failed: {e}")
            return []

    def _keyword_retrieve(self, query: str, top_k: int) -> List[dict]:
        """关键词匹配检索（Jaccard 相似度 + 知识标签匹配）

        复用现有 evolution_service 的 Jaccard 模式，不依赖额外库
        """
        try:
            # 对查询做 2-gram 分词
            query_tokens = set(self._tokenize(query))

            # 从 ChromaDB 获取所有文档（可缓存优化）
            all_docs = self.collection.get(include=["documents", "metadatas"])

            if not all_docs or not all_docs.get("ids"):
                return []

            scored = []
            for i, doc_id in enumerate(all_docs["ids"]):
                doc_text = all_docs["documents"][i] if i < len(all_docs["documents"]) else ""
                doc_meta = all_docs["metadatas"][i] if i < len(all_docs["metadatas"]) else {}

                if not doc_text:
                    continue

                doc_tokens = set(self._tokenize(doc_text))

                # Jaccard 相似度
                intersection = query_tokens & doc_tokens
                union = query_tokens | doc_tokens
                jaccard = len(intersection) / max(1, len(union))

                # 知识标签命中加成
                tag_bonus = 0.0
                if doc_meta.get("module") and _keyword_in_text(doc_meta["module"], query):
                    tag_bonus += 0.15
                if doc_meta.get("title") and _keyword_in_text(doc_meta["title"], query):
                    tag_bonus += 0.10

                score = min(1.0, jaccard + tag_bonus)
                if score > 0.05:  # 最低阈值
                    scored.append({
                        "id": doc_id,
                        "text": doc_text[:800],  # 截断显示
                        "metadata": doc_meta,
                        "score": round(score, 4),
                        "source": "keyword",
                    })

            scored.sort(key=lambda x: x["score"], reverse=True)
            return scored[:top_k]

        except Exception as e:
            logger.warning(f"Keyword retrieval failed: {e}")
            return []

    def _rrf_fusion(
        self,
        dense_results: List[dict],
        keyword_results: List[dict],
        top_k: int,
        k: int = 60,
    ) -> List[dict]:
        """Reciprocal Rank Fusion 融合排序"""
        # 构建 id → chunk 映射
        chunk_map = {}
        for r in dense_results:
            chunk_map[r["id"]] = r
        for r in keyword_results:
            if r["id"] not in chunk_map:
                chunk_map[r["id"]] = r

        # RRF 打分
        rrf_scores = {}
        for rank, r in enumerate(dense_results):
            rrf_scores[r["id"]] = rrf_scores.get(r["id"], 0) + 1.0 / (k + rank + 1)
        for rank, r in enumerate(keyword_results):
            rrf_scores[r["id"]] = rrf_scores.get(r["id"], 0) + 1.0 / (k + rank + 1)

        # 排序
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        results = []
        for doc_id in sorted_ids[:top_k]:
            chunk = chunk_map.get(doc_id, {})
            results.append({
                "id": doc_id,
                "text": chunk.get("text", ""),
                "metadata": chunk.get("metadata", {}),
                "score": round(rrf_scores[doc_id], 4),
                "source": chunk.get("source", "unknown"),
            })

        return results

    def _tokenize(self, text: str) -> List[str]:
        """中文 2-gram 分词"""
        cleaned = text.replace('\n', ' ').replace('\r', ' ')
        tokens = []
        for i in range(len(cleaned) - 1):
            bigram = cleaned[i:i + 2].strip()
            if bigram and ' ' not in bigram:
                tokens.append(bigram)
        return tokens

    # ============================================================
    # 上下文格式化
    # ============================================================

    def format_context(self, chunks: List[dict]) -> str:
        """将检索结果格式化为 Prompt 上下文"""
        if not chunks:
            return ""

        parts = []
        for i, chunk in enumerate(chunks, 1):
            meta = chunk.get("metadata", {})
            source_label = meta.get("source_label", meta.get("title", "未知来源"))
            text = chunk.get("text", "")
            # 截断过长的文本
            if len(text) > 600:
                text = text[:600] + "…"
            parts.append(f"[{i}] ({source_label})\n{text}")

        return RAG_CONTEXT_TEMPLATE.format(chunks="\n\n".join(parts))

    def get_sources(self, chunks: List[dict]) -> List[dict]:
        """提取来源信息（供前端展示）"""
        sources = []
        seen = set()
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            source_key = meta.get("source_path", "")
            if source_key in seen:
                continue
            seen.add(source_key)
            sources.append({
                "title": meta.get("title", "未知来源"),
                "source_path": meta.get("source_path", ""),
                "source_type": meta.get("source_type", ""),
                "section": meta.get("section", ""),
                "page": meta.get("page"),
                "score": chunk.get("score", 0),
            })
        return sources

    # ============================================================
    # 管理方法
    # ============================================================

    def get_status(self) -> dict:
        """获取知识库状态"""
        try:
            count = self.collection.count()
        except Exception:
            count = 0

        return {
            "collection_name": self.collection_name,
            "backend": self.backend.NAME,
            "total_chunks": count,
            "chroma_path": str(self.chroma_path),
        }

    def clear(self):
        """清空知识库"""
        try:
            self.client.delete_collection(self.collection_name)
            self._collection = None
            logger.info(f"已清空知识库: {self.collection_name}")
        except Exception as e:
            logger.warning(f"清空知识库失败: {e}")

    def rebuild(self, chunks: List[DocumentChunk], progress_callback=None) -> dict:
        """清空并重建知识库"""
        self.clear()
        return self.ingest(chunks, progress_callback=progress_callback)


# ============================================================
# 全局单例
# ============================================================

_rag_service_instance: Optional[RAGService] = None


def get_rag_service(
    provider: str = "dashscope",
    api_key: str = "",
    chroma_path: str = DEFAULT_CHROMA_PATH,
    force_reload: bool = False,
) -> RAGService:
    """获取 RAG 服务实例（单例）"""
    global _rag_service_instance

    if _rag_service_instance is not None and not force_reload:
        return _rag_service_instance

    backend = get_embedding_backend(provider=provider, api_key=api_key, force_reload=force_reload)
    _rag_service_instance = RAGService(backend=backend, chroma_path=chroma_path)
    logger.info(f"RAG service initialized: backend={backend.NAME}")
    return _rag_service_instance


def reset_rag_service():
    """重置 RAG 服务（切换 embedding provider 时调用）"""
    global _rag_service_instance
    _rag_service_instance = None
    reset_embedding_backend()


# ============================================================
# 工具函数
# ============================================================

def _keyword_in_text(keyword: str, text: str) -> bool:
    """检查关键词是否在文本中（子串匹配）"""
    if not keyword or not text:
        return False
    return keyword.lower() in text.lower()
