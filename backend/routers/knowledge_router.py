"""知识点管理路由"""
import json
from fastapi import APIRouter
from schemas import APIResponse
from config import KNOWLEDGE_TAGS_PATH

router = APIRouter()

@router.get("/tags", response_model=APIResponse)
async def get_knowledge_tags():
    """获取所有知识点标签"""
    try:
        with open(KNOWLEDGE_TAGS_PATH, 'r', encoding='utf-8') as f:
            tags = json.load(f)
        return APIResponse(data=tags)
    except Exception as e:
        return APIResponse(code=500, message=f"读取失败: {str(e)}")

@router.get("/categories", response_model=APIResponse)
async def get_categories():
    """获取知识点分类列表"""
    try:
        with open(KNOWLEDGE_TAGS_PATH, 'r', encoding='utf-8') as f:
            tags = json.load(f)
        categories = [{"name": t["category"], "tag_count": len(t["tags"])} for t in tags]
        return APIResponse(data=categories)
    except Exception as e:
        return APIResponse(code=500, message=f"读取失败: {str(e)}")
