"""资源推送路由"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from auth import get_current_user
from schemas import APIResponse
from services import resource_service
import httpx

router = APIRouter()

@router.get("/recommend", response_model=APIResponse)
async def get_recommendations(current_user: dict = Depends(get_current_user)):
    """获取个性化推荐资源"""
    resources = resource_service.recommend_resources(current_user["id"])
    return APIResponse(data=resources)

@router.get("/list", response_model=APIResponse)
async def list_resources(category: str = None, difficulty: str = None, page: int = 1, page_size: int = 12):
    """获取资源列表"""
    result = resource_service.get_resources_by_category(category, difficulty, page, page_size)
    return APIResponse(data=result)

@router.post("/collect/{resource_id}", response_model=APIResponse)
async def collect_resource(resource_id: str, current_user: dict = Depends(get_current_user)):
    """收藏/取消收藏资源"""
    result = resource_service.toggle_collect_resource(current_user["id"], resource_id)
    return APIResponse(data=result)

@router.get("/collected", response_model=APIResponse)
async def get_collected(current_user: dict = Depends(get_current_user)):
    """获取收藏资源"""
    resources = resource_service.get_collected_resources(current_user["id"])
    return APIResponse(data=resources)


@router.get("/material", response_model=APIResponse)
async def get_knowledge_material(knowledge: str = "", current_user: dict = Depends(get_current_user)):
    """根据知识点联网搜索+AI整理学习资料（Markdown格式）

    工作流程：
    1. 用Bing搜索知识点相关内容
    2. 抓取搜索结果网页的正文
    3. 由AI整合、组织、去重，生成结构化Markdown学习资料
    """
    try:
        result = await resource_service.search_and_curate_material(
            user_id=current_user["id"],
            knowledge=knowledge
        )
        return APIResponse(data=result)
    except Exception as e:
        return APIResponse(code=500, message=f"获取学习资料失败: {str(e)}", data=None)


@router.get("/learn/{resource_id}", response_model=APIResponse)
async def learn_resource(resource_id: str, current_user: dict = Depends(get_current_user)):
    """点击资源卡片获取学习资料（优先本地，兜底AI联网整理）

    策略：
    1. 用资源ID查找资源，获取其tags
    2. 用tags匹配本地 learning_materials
    3. 本地无匹配时，联网搜索+AI整理
    """
    try:
        result = await resource_service.get_resource_material_async(
            resource_id=resource_id,
            user_id=current_user["id"]
        )
        return APIResponse(data=result)
    except Exception as e:
        return APIResponse(code=500, message=f"获取学习资料失败: {str(e)}", data=None)


@router.get("/proxy-image")
async def proxy_image(url: str = ""):
    """代理获取外部图片，解决浏览器跨域/混合内容拦截问题"""
    if not url:
        raise HTTPException(status_code=400, detail="url parameter required")
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                content_type = resp.headers.get("content-type", "image/png")
                return StreamingResponse(
                    content=iter([resp.content]),
                    media_type=content_type,
                    headers={"Cache-Control": "public, max-age=86400"}
                )
            raise HTTPException(status_code=resp.status_code, detail="Image fetch failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
