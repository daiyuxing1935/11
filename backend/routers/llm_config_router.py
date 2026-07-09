"""用户LLM配置路由 — 支持用户自行配置API Key/Base URL/模型"""
from fastapi import APIRouter, Depends
from auth import get_current_user
from schemas import APIResponse, LLMConfigRequest, LLMConfigResponse
from database import get_db
from datetime import datetime

router = APIRouter()


def _mask_api_key(key: str) -> str:
    """对API Key做脱敏处理，仅显示前4位和后4位"""
    if not key:
        return ""
    if len(key) <= 8:
        return key[:2] + "***"
    return key[:4] + "***" + key[-4:]


@router.get("", response_model=APIResponse)
async def get_llm_config(current_user: dict = Depends(get_current_user)):
    """获取当前用户的LLM配置（API Key脱敏）"""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM user_llm_config WHERE user_id = ?",
        (current_user["id"],)
    ).fetchone()
    conn.close()

    if row:
        r = dict(row)
        return APIResponse(data=LLMConfigResponse(
            provider=r.get("provider", "openai"),
            api_key=_mask_api_key(r.get("api_key", "")),
            base_url=r.get("base_url", "https://api.openai.com"),
            model_name=r.get("model_name", "gpt-4o"),
            temperature=r.get("temperature", 0.7),
            max_tokens=r.get("max_tokens", 4096),
            is_configured=bool(r.get("api_key")),
            image_api_key=_mask_api_key(r.get("image_api_key", ""))
        ).model_dump())
    else:
        return APIResponse(data=LLMConfigResponse(is_configured=False).model_dump())


@router.put("", response_model=APIResponse)
async def save_llm_config(req: LLMConfigRequest, current_user: dict = Depends(get_current_user)):
    """保存/更新用户的LLM配置"""
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM user_llm_config WHERE user_id = ?",
        (current_user["id"],)
    ).fetchone()

    now = datetime.now().isoformat()
    if existing:
        conn.execute(
            """UPDATE user_llm_config
               SET provider=?, api_key=?, base_url=?, model_name=?,
                   temperature=?, max_tokens=?, image_api_key=?, updated_at=?
               WHERE user_id=?""",
            (req.provider, req.api_key, req.base_url, req.model_name,
             req.temperature, req.max_tokens, req.image_api_key or "", now, current_user["id"])
        )
    else:
        conn.execute(
            """INSERT INTO user_llm_config
               (user_id, provider, api_key, base_url, model_name, temperature, max_tokens, image_api_key, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (current_user["id"], req.provider, req.api_key, req.base_url,
             req.model_name, req.temperature, req.max_tokens, req.image_api_key or "", now)
        )
    conn.commit()
    conn.close()

    return APIResponse(data={
        "message": "LLM配置已保存",
        "model_name": req.model_name,
        "base_url": req.base_url,
        "is_configured": bool(req.api_key)
    })


@router.delete("", response_model=APIResponse)
async def reset_llm_config(current_user: dict = Depends(get_current_user)):
    """重置用户的LLM配置为系统默认"""
    conn = get_db()
    conn.execute(
        "DELETE FROM user_llm_config WHERE user_id = ?",
        (current_user["id"],)
    )
    conn.commit()
    conn.close()
    return APIResponse(data={"message": "已重置为系统默认配置"})
