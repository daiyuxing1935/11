"""AI 配图生成服务 — 使用 LLM 直接生成 SVG 矢量图"""
import os
import json
import hashlib
import httpx
import re
from database import get_db
from datetime import datetime
from services.ai_service import call_llm

IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "generated_images")
os.makedirs(IMAGES_DIR, exist_ok=True)


def _init_image_table():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS generated_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            prompt_hash TEXT NOT NULL,
            prompt_text TEXT NOT NULL,
            svg_content TEXT,
            file_path TEXT,
            provider TEXT DEFAULT 'llm-svg',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_img_hash2 ON generated_images(prompt_hash)")
    conn.commit()
    conn.close()

_init_image_table()


async def generate_image(user_id: int, prompt: str, style: str = "educational") -> dict:
    """使用 LLM 生成教育配图 SVG"""
    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()

    # 检查缓存
    conn = get_db()
    cached = conn.execute(
        "SELECT svg_content, file_path FROM generated_images WHERE prompt_hash = ? AND svg_content IS NOT NULL LIMIT 1",
        (prompt_hash,)
    ).fetchone()
    conn.close()
    if cached and cached["svg_content"]:
        return {
            "success": True,
            "svg": cached["svg_content"],
            "cached": True
        }

    # 构建 LLM 提示词
    svg_prompt = f"""你是一位教育插画师。请为教科书创建一张清晰的中文 SVG 插图。

知识点："{prompt}"

关键规则：
- ViewBox 0 0 800 500
- 扁平化 2D 矢量图，科技蓝 #409EFF + 白色 + 深蓝 #1a1a2e
- 浅蓝渐变背景 (#f0f7ff 到 #e8f2fb)
- **所有文字标签必须使用中文**
- 所有文字字号 14px 以上
- 元素之间至少垂直间距 40px、水平间距 30px
- 充分留白，不要拥挤
- 禁止元素重叠
- 最多 6-8 个标注元素
- 标注用简短词组（3-6个字）
- 每个方框/标签至少 120x40 像素
- 文字不能遮挡其他文字或图形

只输出 SVG 代码，用 ```svg 和 ``` 包裹。"""

    try:
        llm_response = await call_llm(
            user_id=user_id,
            messages=[{"role": "user", "content": svg_prompt}],
            temperature=0.7,
            max_tokens=4096
        )
        if not llm_response or llm_response.startswith("LLM调用异常"):
            return {"success": False, "error": f"LLM 调用失败: {llm_response}"}

        # 提取 SVG 代码
        svg_match = re.search(r'```svg\s*(.*?)\s*```', llm_response, re.DOTALL)
        if not svg_match:
            svg_match = re.search(r'<svg\s.*?</svg>', llm_response, re.DOTALL)
        if svg_match:
            svg_code = svg_match.group(1) if '```' in llm_response else svg_match.group(0)
        else:
            # 尝试直接解析
            svg_code = llm_response.strip()

        svg_code = svg_code.strip()
        if not svg_code.startswith('<svg'):
            return {"success": False, "error": "LLM 未能生成有效 SVG"}

        # 确保 viewBox 正确
        if 'viewBox=' not in svg_code[:200]:
            svg_code = svg_code.replace('<svg', '<svg viewBox="0 0 800 500"')

        # 保存
        file_path = os.path.join(IMAGES_DIR, f"{prompt_hash}.svg")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(svg_code)

        conn = get_db()
        conn.execute(
            "INSERT OR REPLACE INTO generated_images (user_id, prompt_hash, prompt_text, svg_content, file_path, provider, created_at) VALUES (?, ?, ?, ?, ?, 'llm-svg', ?)",
            (user_id, prompt_hash, prompt, svg_code, file_path, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

        return {"success": True, "svg": svg_code, "cached": False}

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_cached_images(user_id: int) -> list:
    conn = get_db()
    rows = conn.execute(
        "SELECT id, prompt_hash, prompt_text, provider, created_at FROM generated_images WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [{
        "id": r["id"],
        "prompt_hash": r["prompt_hash"],
        "prompt_text": r["prompt_text"][:200] + "...",
        "provider": r["provider"],
        "created_at": r["created_at"]
    } for r in rows]
