"""Pydantic请求/响应模型"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# ===== Auth =====
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    nickname: Optional[str] = ""
    grade: Optional[str] = ""
    learning_stage: Optional[str] = "入门"
    learning_goal: Optional[str] = ""

class UserLogin(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    grade: Optional[str] = None
    learning_stage: Optional[str] = None
    learning_goal: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    nickname: str
    grade: str
    learning_stage: str
    learning_goal: str
    avatar: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# ===== Diagnosis =====
class QuizGenerateRequest(BaseModel):
    stage: str = "入门"
    count: int = Field(default=10, ge=1, le=50)
    focus_knowledge: Optional[List[str]] = None
    use_timer: bool = False
    timer_minutes: int = Field(default=30, ge=1, le=180)

class QuizAnswer(BaseModel):
    question_id: str
    user_answer: str

class QuizSubmitRequest(BaseModel):
    session_id: int
    answers: List[QuizAnswer]

class QuizQuestion(BaseModel):
    question_id: str
    question: str
    options: Optional[List[str]] = None
    question_type: str
    difficulty: str
    knowledge_tag: str

class QuizReport(BaseModel):
    score: float
    total: int
    correct_rate: float
    knowledge_analysis: Dict[str, Any]
    weak_points: List[str]
    strong_points: List[str]
    suggestions: List[str]

# ===== Q&A =====
class QARequest(BaseModel):
    question: str
    question_type: str = "text"  # text, code, algorithm
    explanation_level: str = "standard"  # beginner, standard, advanced
    context: Optional[str] = ""
    deep_thinking: bool = False     # 深度思考模式
    enable_search: bool = False     # 联网搜索
    file_text: Optional[str] = None  # 上传文件提取的文本内容
    file_base64: Optional[str] = None  # 上传图片的 base64 data URL (如 data:image/png;base64,...)
    history: Optional[List[Dict[str, str]]] = None  # 多轮对话历史 [{role, content}, ...]
    use_rag: bool = True  # 是否启用 RAG 知识库增强

class QAResponse(BaseModel):
    id: int
    question: str
    answer: str
    knowledge_tags: str
    created_at: str

class QASaveRequest(BaseModel):
    question: str
    answer: str
    question_type: str = "text"
    explanation_level: str = "standard"

class QAFeedbackRequest(BaseModel):
    qa_history_id: int
    rating: int  # 1=有用, -1=无用
    feedback_text: str = ""

class CodeRunRequest(BaseModel):
    code: str = Field(..., min_length=1)
    language: str = "python"  # python, javascript, c, cpp, java

# ===== Learning Path =====
class LearningPathGenerateRequest(BaseModel):
    goal: str = ""
    timeline: str = ""
    learning_depth: str = Field(default="标准")  # 基础/标准/深入
    diagnostic_session_id: Optional[int] = None
    modules: Optional[List[str]] = None  # 选中的模块名列表，如 ["智能体基础通识", "大模型与提示词工程"]

class DiagnosticTestRequest(BaseModel):
    goal: str = ""
    count: int = Field(default=10, ge=5, le=30)

class PathProgressUpdateRequest(BaseModel):
    task_key: str
    completed: bool = True
    sub_action: Optional[str] = None  # "learn" | "quiz" | "code" | None=全标记

class TaskUpdate(BaseModel):
    completed: int = 1

class TaskQuizRequest(BaseModel):
    task_day: int = Field(..., ge=1)
    count: int = Field(default=10, ge=1, le=50)

class CodeExecuteRequest(BaseModel):
    task_day: int = Field(..., ge=1)
    code: str = Field(..., min_length=1)

class CodeStepGuideRequest(BaseModel):
    task_day: int = Field(..., ge=1)

class CodeStepCheckRequest(BaseModel):
    task_day: int = Field(..., ge=1)
    step_index: int = Field(..., ge=0)
    code: str = Field(..., min_length=1)
    step_title: str = Field(default="")
    step_instruction: str = Field(default="")

# ===== Stats =====
class StatsResponse(BaseModel):
    total_study_duration: int
    total_questions: int
    avg_correct_rate: float
    knowledge_mastery: Dict[str, float]
    weekly_stats: List[Dict[str, Any]]
    recent_records: List[Dict[str, Any]]

# ===== LLM Config =====
class LLMConfigRequest(BaseModel):
    provider: Optional[str] = "openai"
    api_key: Optional[str] = ""
    base_url: Optional[str] = "https://api.openai.com"
    model_name: Optional[str] = "gpt-4o"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096
    image_api_key: Optional[str] = ""  # Replicate API key for image generation
    embedding_api_key: Optional[str] = ""  # DashScope API key for RAG embedding
    embedding_provider: Optional[str] = "dashscope"
    embedding_model: Optional[str] = "text-embedding-v3"

class LLMConfigResponse(BaseModel):
    provider: str = "openai"
    api_key: str = ""  # masked: "sk-a...b1f2"
    base_url: str = "https://api.openai.com"
    model_name: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    is_configured: bool = False  # whether user has set a custom config
    image_api_key: str = ""  # masked: "r8_...xyz"
    embedding_api_key: str = ""  # masked
    embedding_provider: str = "dashscope"
    embedding_model: str = "text-embedding-v3"

# ===== Common =====
class APIResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Any = None
