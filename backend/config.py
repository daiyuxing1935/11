"""应用配置"""
import os

# JWT配置
SECRET_KEY = "ai-agent-learning-platform-secret-key-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天

# 数据库配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "data", "learning_platform.db")
KNOWLEDGE_TAGS_PATH = os.path.join(BASE_DIR, "data", "knowledge_tags.json")
RESOURCES_PATH = os.path.join(BASE_DIR, "data", "resources.json")

# 题库目录（backend/data/dataset/ 下）
DATASET_DIR = os.path.join(BASE_DIR, "data", "dataset")

# RAG 知识库配置
CHROMA_DB_PATH = os.path.join(BASE_DIR, "data", "chroma_db")
RAG_TOP_K = 5
RAG_DEFAULT_EMBEDDING_PROVIDER = "dashscope"  # "dashscope" | "bge"

# 出题配置
MAX_QUESTIONS_PER_QUIZ = 20
QUESTION_TYPES = ["单选", "多选", "判断", "简答", "填空", "代码实操"]
DIFFICULTY_LEVELS = ["Lv1入门", "Lv2中等", "Lv3高阶"]
LEARNING_STAGES = ["入门", "进阶", "高阶"]

# 知识点权重配置
WEAK_POINT_WEIGHT = 0.6   # 薄弱知识点出题权重
MASTERED_WEIGHT = 0.2     # 已掌握知识点出题权重
NORMAL_WEIGHT = 0.2       # 一般知识点出题权重
