"""伴随式学习路由"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth import get_current_user
from schemas import APIResponse, LearningPathGenerateRequest, PathProgressUpdateRequest, TaskUpdate, TaskQuizRequest, CodeExecuteRequest, CodeStepGuideRequest, CodeStepCheckRequest, DiagnosticTestRequest
from services import learning_service, resource_service

router = APIRouter()

@router.post("/path/generate", response_model=APIResponse)
async def generate_path(req: LearningPathGenerateRequest, current_user: dict = Depends(get_current_user)):
    """生成个性化学习路径（可选携带诊断测试结果）"""
    try:
        result = await learning_service.generate_learning_path(
            user_id=current_user["id"],
            goal=req.goal,
            timeline=req.timeline,
            learning_depth=req.learning_depth,
            diagnostic_session_id=req.diagnostic_session_id,
            modules=req.modules
        )
        return APIResponse(data=result)
    except ValueError as e:
        return APIResponse(code=400, message=str(e), data=None)
    except Exception as e:
        return APIResponse(code=500, message=f"生成学习路径失败: {str(e)}", data=None)

@router.delete("/path", response_model=APIResponse)
async def delete_path(current_user: dict = Depends(get_current_user)):
    """删除当前学习路径"""
    try:
        result = await learning_service.delete_learning_path(current_user["id"])
        return APIResponse(data=result)
    except Exception as e:
        return APIResponse(code=500, message=f"删除学习路径失败: {str(e)}", data=None)

@router.post("/path/diagnostic-test", response_model=APIResponse)
async def create_diagnostic_test(req: DiagnosticTestRequest, current_user: dict = Depends(get_current_user)):
    """根据学习目标生成诊断测试卷"""
    try:
        result = await learning_service.generate_diagnostic_test(
            user_id=current_user["id"],
            goal=req.goal,
            count=req.count
        )
        return APIResponse(data=result)
    except Exception as e:
        return APIResponse(code=500, message=f"生成诊断测试失败: {str(e)}", data=None)

@router.get("/resource", response_model=APIResponse)
async def get_learning_resource(knowledge: str = "", current_user: dict = Depends(get_current_user)):
    """根据知识点获取本地学习资料（Markdown格式）"""
    try:
        result = resource_service.get_local_material(knowledge)
        if result and result.get("found"):
            return APIResponse(data=result)
        # 如果没找到本地资料，返回fallback内容
        return APIResponse(data=result)
    except Exception as e:
        return APIResponse(code=500, message=f"获取学习资源失败: {str(e)}", data=None)

@router.get("/path", response_model=APIResponse)
async def get_path(current_user: dict = Depends(get_current_user)):
    """获取当前学习路径"""
    result = await learning_service.get_learning_path(current_user["id"])
    return APIResponse(data=result)

@router.put("/path/progress", response_model=APIResponse)
async def update_progress(req: PathProgressUpdateRequest, current_user: dict = Depends(get_current_user)):
    """更新路径进度（sub_action: learn/quiz/code，不传则全标记）"""
    result = await learning_service.update_path_progress(
        current_user["id"], req.task_key, req.completed, req.sub_action
    )
    return APIResponse(data=result)

@router.get("/tasks", response_model=APIResponse)
async def get_tasks(date: str = None, current_user: dict = Depends(get_current_user)):
    """获取每日任务"""
    result = await learning_service.get_daily_tasks(current_user["id"], date)
    return APIResponse(data=result)

@router.put("/tasks/complete", response_model=APIResponse)
async def complete_task(req: TaskUpdate, date: str = "", current_user: dict = Depends(get_current_user)):
    """完成每日任务"""
    if not date:
        from datetime import datetime
        date = datetime.now().strftime("%Y-%m-%d")
    result = await learning_service.update_daily_task(current_user["id"], date, req.completed)
    return APIResponse(data=result)

@router.post("/task-quiz", response_model=APIResponse)
async def generate_task_quiz(req: TaskQuizRequest, current_user: dict = Depends(get_current_user)):
    """为学习路径中指定天数的任务生成专项练习题"""
    try:
        result = await learning_service.generate_task_quiz(
            user_id=current_user["id"],
            task_day=req.task_day,
            count=req.count
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return APIResponse(data=result)
    except HTTPException:
        raise
    except Exception as e:
        return APIResponse(code=500, message=f"生成任务练习失败: {str(e)}", data=None)

@router.get("/code-task/{task_day}", response_model=APIResponse)
async def get_code_task(task_day: int, current_user: dict = Depends(get_current_user)):
    """获取指定天数的编程任务"""
    try:
        result = await learning_service.get_code_task(current_user["id"], task_day)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return APIResponse(data=result)
    except HTTPException:
        raise
    except Exception as e:
        return APIResponse(code=500, message=f"获取编程任务失败: {str(e)}", data=None)

@router.post("/code-execute", response_model=APIResponse)
async def execute_code(req: CodeExecuteRequest, current_user: dict = Depends(get_current_user)):
    """执行用户代码并运行测试"""
    try:
        result = await learning_service.execute_code(current_user["id"], req.task_day, req.code)
        # 记录代码完成
        if not result.get("error"):
            try:
                await learning_service.record_code_completion(current_user["id"], req.task_day)
            except Exception:
                pass
        return APIResponse(data=result)
    except Exception as e:
        return APIResponse(code=500, message=f"代码执行失败: {str(e)}", data=None)

@router.get("/code-answer/{task_day}", response_model=APIResponse)
async def get_code_answer(task_day: int, current_user: dict = Depends(get_current_user)):
    """获取编程任务参考答案及逐行解释"""
    try:
        result = await learning_service.get_code_answer(current_user["id"], task_day)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return APIResponse(data=result)
    except HTTPException:
        raise
    except Exception as e:
        return APIResponse(code=500, message=f"获取参考答案失败: {str(e)}", data=None)

@router.post("/code-step-guide", response_model=APIResponse)
async def generate_step_guide(req: CodeStepGuideRequest, current_user: dict = Depends(get_current_user)):
    """AI 将编程任务分解为手把手教学步骤"""
    try:
        result = await learning_service.generate_code_step_guide(current_user["id"], req.task_day)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return APIResponse(data=result)
    except HTTPException:
        raise
    except Exception as e:
        return APIResponse(code=500, message=f"生成教学步骤失败: {str(e)}", data=None)

@router.post("/code-step-check", response_model=APIResponse)
async def check_code_step(req: CodeStepCheckRequest, current_user: dict = Depends(get_current_user)):
    """AI 检查当前步骤代码是否正确"""
    try:
        result = await learning_service.check_code_step(
            current_user["id"], req.task_day, req.step_index, req.code,
            req.step_title, req.step_instruction
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return APIResponse(data=result)
    except HTTPException:
        raise
    except Exception as e:
        return APIResponse(code=500, message=f"检查代码步骤失败: {str(e)}", data=None)

@router.get("/error-book", response_model=APIResponse)
async def get_error_book(page: int = 1, page_size: int = 20, current_user: dict = Depends(get_current_user)):
    """获取错题本"""
    result = await learning_service.get_error_book(current_user["id"], page, page_size)
    return APIResponse(data=result)

@router.put("/error-book/{error_id}/review", response_model=APIResponse)
async def review_error(error_id: int, current_user: dict = Depends(get_current_user)):
    """标记错题已复习"""
    result = await learning_service.review_error(current_user["id"], error_id)
    return APIResponse(data=result)

class BatchDeleteRequest(BaseModel):
    ids: list[int]

@router.get("/error-book/sessions", response_model=APIResponse)
async def get_error_sessions(current_user: dict = Depends(get_current_user)):
    """获取错题按测评分组"""
    result = await learning_service.get_error_sessions(current_user["id"])
    return APIResponse(data=result)

@router.get("/error-book/session/{session_id}", response_model=APIResponse)
async def get_errors_by_session(session_id: int, page: int = 1, current_user: dict = Depends(get_current_user)):
    """获取指定会话的错题"""
    result = await learning_service.get_errors_by_session(current_user["id"], session_id, page)
    return APIResponse(data=result)

@router.get("/error-book/orphan", response_model=APIResponse)
async def get_orphan_errors(page: int = 1, current_user: dict = Depends(get_current_user)):
    """获取无会话的历史错题"""
    result = await learning_service.get_errors_by_session(current_user["id"], None, page)
    return APIResponse(data=result)

@router.delete("/error-book/session/{session_id}", response_model=APIResponse)
async def delete_session_errors(session_id: int, current_user: dict = Depends(get_current_user)):
    """删除某次测评的全部错题"""
    result = await learning_service.delete_errors_by_session(current_user["id"], session_id)
    return APIResponse(data=result)

@router.delete("/error-book/orphan", response_model=APIResponse)
async def delete_orphan_errors(current_user: dict = Depends(get_current_user)):
    """删除历史错题"""
    result = await learning_service.delete_errors_by_session(current_user["id"], None)
    return APIResponse(data=result)

@router.post("/error-book/batch-delete", response_model=APIResponse)
async def batch_delete_errors(req: BatchDeleteRequest, current_user: dict = Depends(get_current_user)):
    """批量删除错题（保留兼容）"""
    result = await learning_service.batch_delete_errors(current_user["id"], req.ids)
    return APIResponse(data=result)
