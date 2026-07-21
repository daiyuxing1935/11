"""嵌入服务 — 双后端（阿里云 DashScope text-embedding-v3 + 本地 BAAI/bge-large-zh-v1.5）

生产环境：用户配置 dashscope API Key → 使用云端 text-embedding-v3（1024维）
本地/离线环境：自动降级到 bge-large-zh-v1.5（1024维，GPU/CPU推理）
"""

import os
import hashlib
import logging
from typing import List, Optional

# HuggingFace 国内镜像加速
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

logger = logging.getLogger(__name__)

# ============================================================
# 嵌入后端抽象
# ============================================================

class EmbeddingBackend:
    """嵌入后端基类"""
    DIMENSION = 1024
    NAME = "base"

    def embed(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

    def embed_single(self, text: str) -> List[float]:
        results = self.embed([text])
        return results[0]


# ============================================================
# 阿里云 DashScope 后端（生产环境）
# ============================================================

class DashScopeBackend(EmbeddingBackend):
    """阿里云 text-embedding-v3 云端嵌入"""
    NAME = "dashscope-text-embedding-v3"
    BATCH_SIZE = 25  # DashScope 单次最大 25 条

    def __init__(self, api_key: str, model: str = "text-embedding-v3"):
        import dashscope
        dashscope.api_key = api_key
        self.model = model
        self._dashscope = dashscope

    def embed(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入，自动分批"""
        if not texts:
            return []

        all_embeddings = []
        for i in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[i:i + self.BATCH_SIZE]
            for text in batch:
                resp = self._dashscope.TextEmbedding.call(
                    model=self.model,
                    input=text
                )
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"DashScope embedding failed: code={resp.status_code}, "
                        f"message={getattr(resp, 'message', 'unknown')}"
                    )
                emb = resp.output['embeddings'][0]['embedding']
                all_embeddings.append(emb)

        return all_embeddings


# ============================================================
# 本地 BGE 后端（离线/降级）
# ============================================================

class BGELocalBackend(EmbeddingBackend):
    """BAAI/bge-large-zh-v1.5 本地推理"""
    NAME = "bge-large-zh-v1.5"
    BATCH_SIZE = 32

    def __init__(self, device: str = None):
        from sentence_transformers import SentenceTransformer

        if device is None:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info(f"Loading BAAI/bge-large-zh-v1.5 on {device} ...")
        self.model = SentenceTransformer(
            "BAAI/bge-large-zh-v1.5",
            device=device,
        )
        self._device = device
        logger.info(f"BGE model loaded on {device}")

    def embed(self, texts: List[str]) -> List[List[float]]:
        """本地批量推理"""
        if not texts:
            return []

        # bge-large-zh-v1.5 自带中文优化，无需额外 prefix
        embeddings = self.model.encode(
            texts,
            batch_size=self.BATCH_SIZE,
            show_progress_bar=False,
            normalize_embeddings=True,  # 归一化到单位向量，便于余弦相似度
        )
        return embeddings.tolist()


# ============================================================
# 嵌入缓存层（避免重复调用 API）
# ============================================================

class CachedEmbeddingBackend(EmbeddingBackend):
    """嵌入缓存装饰器 — 对相同文本避免重复调用 API"""

    def __init__(self, backend: EmbeddingBackend):
        self._backend = backend
        self._cache: dict = {}
        self.NAME = f"cached-{backend.NAME}"
        self.DIMENSION = backend.DIMENSION

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def embed(self, texts: List[str]) -> List[List[float]]:
        results = []
        uncached_texts = []
        uncached_indices = []

        for i, text in enumerate(texts):
            key = self._hash(text)
            if key in self._cache:
                results.append((i, self._cache[key]))
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
                results.append((i, None))  # placeholder

        if uncached_texts:
            new_embs = self._backend.embed(uncached_texts)
            for idx, text, emb in zip(uncached_indices, uncached_texts, new_embs):
                key = self._hash(text)
                self._cache[key] = emb
                results[idx] = (idx, emb)

        # 按原始顺序返回
        results.sort(key=lambda x: x[0])
        return [r[1] for r in results]

    def clear_cache(self):
        self._cache.clear()


# ============================================================
# 工厂函数
# ============================================================

# 全局单例（避免重复加载模型）
_backend_instance: Optional[EmbeddingBackend] = None


def get_embedding_backend(
    provider: str = "dashscope",
    api_key: str = "",
    model: str = "text-embedding-v3",
    force_reload: bool = False,
) -> EmbeddingBackend:
    """获取嵌入后端实例（单例模式）

    Args:
        provider: "dashscope" | "bge"
        api_key: 仅 dashscope 需要
        model: dashscope 模型名
        force_reload: 强制重新创建实例

    Returns:
        EmbeddingBackend 实例（带缓存层）
    """
    global _backend_instance

    if _backend_instance is not None and not force_reload:
        return _backend_instance

    if provider == "dashscope":
        if not api_key:
            raise ValueError(
                "DashScope 嵌入需要 API Key。请在「个人中心 → Embedding 配置」中设置你的阿里云 API Key。"
            )
        backend = DashScopeBackend(api_key=api_key, model=model)
    elif provider == "bge":
        backend = BGELocalBackend()
    else:
        raise ValueError(f"不支持的嵌入提供商: {provider}。可选: dashscope, bge")

    _backend_instance = CachedEmbeddingBackend(backend)
    logger.info(f"Embedding backend: {_backend_instance.NAME}")
    return _backend_instance


def reset_embedding_backend():
    """重置嵌入后端（切换 provider 时调用）"""
    global _backend_instance
    _backend_instance = None


def test_dashscope_connection(api_key: str, model: str = "text-embedding-v3") -> dict:
    """测试 DashScope API 连通性

    Returns:
        {"ok": True/False, "dimension": int, "latency_ms": float, "error": str}
    """
    import time
    try:
        backend = DashScopeBackend(api_key=api_key, model=model)
        t0 = time.time()
        emb = backend.embed_single("连通性测试")
        latency = (time.time() - t0) * 1000
        return {
            "ok": True,
            "dimension": len(emb),
            "latency_ms": round(latency, 1),
            "model": model,
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
        }
