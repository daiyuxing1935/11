"""编程能力验证闭环 API。"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import get_current_user
from schemas import APIResponse
from services import capability_service


router = APIRouter()


class SessionStartRequest(BaseModel):
    exercise_id: str = Field(min_length=1, max_length=40)
    force_new: bool = False


class EventBatchRequest(BaseModel):
    events: list[dict] = []


class CodePassedRequest(BaseModel):
    code: str = Field(min_length=1, max_length=200_000)


class DefenseRequest(BaseModel):
    answers: list[dict]
    ai_usage: str = "未使用"


class RepairRequest(BaseModel):
    code: str = Field(min_length=1, max_length=200_000)
    explanation: str = Field(min_length=1, max_length=3000)


def _bad_request(exc: Exception):
    raise HTTPException(status_code=400, detail=str(exc))


@router.post("/sessions", response_model=APIResponse)
async def start_session(req: SessionStartRequest, current_user: dict = Depends(get_current_user)):
    try:
        return APIResponse(data=capability_service.start_session(
            current_user["id"], req.exercise_id, req.force_new
        ))
    except Exception as exc:
        _bad_request(exc)


@router.get("/sessions/{session_id}", response_model=APIResponse)
async def get_session(session_id: int, current_user: dict = Depends(get_current_user)):
    try:
        return APIResponse(data=capability_service.get_session(current_user["id"], session_id))
    except Exception as exc:
        _bad_request(exc)


@router.post("/sessions/{session_id}/events", response_model=APIResponse)
async def record_events(session_id: int, req: EventBatchRequest, current_user: dict = Depends(get_current_user)):
    try:
        return APIResponse(data=capability_service.record_events(current_user["id"], session_id, req.events))
    except Exception as exc:
        _bad_request(exc)


@router.post("/sessions/{session_id}/code-passed", response_model=APIResponse)
async def mark_code_passed(session_id: int, req: CodePassedRequest, current_user: dict = Depends(get_current_user)):
    try:
        return APIResponse(data=capability_service.mark_code_passed(current_user["id"], session_id, req.code))
    except Exception as exc:
        _bad_request(exc)


@router.post("/sessions/{session_id}/defense", response_model=APIResponse)
async def submit_defense(session_id: int, req: DefenseRequest, current_user: dict = Depends(get_current_user)):
    try:
        return APIResponse(data=await capability_service.submit_defense(
            current_user["id"], session_id, req.answers, req.ai_usage
        ))
    except Exception as exc:
        _bad_request(exc)


@router.post("/sessions/{session_id}/repair", response_model=APIResponse)
async def submit_repair(session_id: int, req: RepairRequest, current_user: dict = Depends(get_current_user)):
    try:
        return APIResponse(data=capability_service.submit_repair(
            current_user["id"], session_id, req.code, req.explanation
        ))
    except Exception as exc:
        _bad_request(exc)


@router.post("/sessions/{session_id}/skip", response_model=APIResponse)
async def skip_capability(session_id: int, current_user: dict = Depends(get_current_user)):
    """跳过能力验证，仅以测试分数完成关卡。"""
    try:
        return APIResponse(data=capability_service.skip_capability(
            current_user["id"], session_id
        ))
    except Exception as exc:
        _bad_request(exc)


@router.get("/sessions/{session_id}/review", response_model=APIResponse)
async def review_session(session_id: int, current_user: dict = Depends(get_current_user)):
    """获取能力验证回顾数据，包含用户回答与标准答案对比。"""
    try:
        return APIResponse(data=await capability_service.get_session_review(
            current_user["id"], session_id
        ))
    except Exception as exc:
        _bad_request(exc)


@router.get("/scores", response_model=APIResponse)
async def get_scores(current_user: dict = Depends(get_current_user)):
    """获取所有已完成的实验关卡分数。"""
    try:
        return APIResponse(data=capability_service.get_exercise_scores(current_user["id"]))
    except Exception as exc:
        _bad_request(exc)

