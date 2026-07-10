"""数据库初始化与连接管理"""
import sqlite3
import os
from config import DATABASE_PATH

def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def _run_migration(conn, table, column_sql, label):
    """安全执行数据库迁移（列已存在则跳过）"""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_sql}")
        conn.commit()
        print(f"[OK] {label}")
    except Exception:
        pass  # 列已存在，忽略

def init_db():
    """初始化数据库，创建所有表"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = get_db()

    # 使用 connection.executescript 而非 cursor.executescript，
    # 避免 cursor 状态异常导致后续 migration 静默失败
    conn.executescript("""
        -- 用户表
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nickname TEXT DEFAULT '',
            grade TEXT DEFAULT '',
            learning_stage TEXT DEFAULT '入门',
            learning_goal TEXT DEFAULT '',
            avatar TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 知识点标签表
        CREATE TABLE IF NOT EXISTS knowledge_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT DEFAULT '',
            parent_id INTEGER DEFAULT 0
        );

        -- 测评会话表
        CREATE TABLE IF NOT EXISTS quiz_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stage TEXT DEFAULT '入门',
            questions_json TEXT DEFAULT '[]',
            answers_json TEXT DEFAULT '[]',
            score REAL DEFAULT 0,
            total INTEGER DEFAULT 0,
            report_json TEXT DEFAULT '{}',
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- 错题本
        CREATE TABLE IF NOT EXISTS error_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_id INTEGER,
            question_data TEXT NOT NULL,
            user_answer TEXT DEFAULT '',
            correct_answer TEXT DEFAULT '',
            error_type TEXT DEFAULT '',
            knowledge_tag TEXT DEFAULT '',
            reviewed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- 问答历史
        CREATE TABLE IF NOT EXISTS qa_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            question_type TEXT DEFAULT 'text',
            knowledge_tags TEXT DEFAULT '',
            explanation_level TEXT DEFAULT 'standard',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- 学习路径
        CREATE TABLE IF NOT EXISTS learning_paths (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            path_data_json TEXT DEFAULT '{}',
            progress_json TEXT DEFAULT '{}',
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- 每日任务
        CREATE TABLE IF NOT EXISTS daily_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_data_json TEXT DEFAULT '{}',
            completed INTEGER DEFAULT 0,
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- 学习记录
        CREATE TABLE IF NOT EXISTS learning_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            knowledge_tag TEXT DEFAULT '',
            action_type TEXT DEFAULT '',
            duration_seconds INTEGER DEFAULT 0,
            result_json TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- 资源收藏
        CREATE TABLE IF NOT EXISTS user_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            resource_id TEXT NOT NULL,
            collected INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- 用户LLM配置表
        CREATE TABLE IF NOT EXISTS user_llm_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            provider TEXT DEFAULT 'openai',
            api_key TEXT DEFAULT '',
            base_url TEXT DEFAULT 'https://api.openai.com',
            model_name TEXT DEFAULT 'gpt-4o',
            temperature REAL DEFAULT 0.7,
            max_tokens INTEGER DEFAULT 4096,
            image_api_key TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- 学习统计
        CREATE TABLE IF NOT EXISTS learning_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            study_duration INTEGER DEFAULT 0,
            questions_done INTEGER DEFAULT 0,
            correct_rate REAL DEFAULT 0,
            knowledge_mastery_json TEXT DEFAULT '{}',
            mastery_detail_json TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, date)
        );

        -- 问答反馈（自进化：👍👎）
        CREATE TABLE IF NOT EXISTS qa_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qa_history_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            feedback_text TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (qa_history_id) REFERENCES qa_history(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- 成功模式记忆库（自进化：高质量问答模板）
        CREATE TABLE IF NOT EXISTS qa_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT NOT NULL,
            answer_text TEXT NOT NULL,
            knowledge_tags TEXT DEFAULT '',
            success_count INTEGER DEFAULT 0,
            usage_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 数据库迁移（使用 conn.execute 而非 cursor.execute，避免 executescript 后 cursor 状态异常）
    _run_migration(conn, "error_questions", "session_id INTEGER", "错题表迁移: 添加 session_id 列")
    _run_migration(conn, "user_llm_config", "image_api_key TEXT DEFAULT ''", "LLM配置表迁移: 添加 image_api_key 列")
    _run_migration(conn, "learning_stats", "mastery_detail_json TEXT DEFAULT '{}'", "学习统计表迁移: 添加 mastery_detail_json 列")

    # Seed demo user
    try:
        from auth import hash_password
        existing = conn.execute("SELECT id FROM users WHERE username = 'demo'").fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO users (username, password_hash, nickname, grade, learning_stage, learning_goal) VALUES (?, ?, ?, ?, ?, ?)",
                ("demo", hash_password("demo123"), "Demo学员", "大一/计算机科学", "入门", "系统掌握AI智能体学科知识")
            )
            conn.execute(
                "INSERT INTO learning_stats (user_id, date, study_duration, questions_done, correct_rate) VALUES (1, date('now'), 45, 12, 0.75)"
            )
            print("[OK] Demo account created: demo / demo123")
    except Exception as e:
        print(f"[WARN] Demo seed failed: {e}")

    conn.commit()
    conn.close()
    print("[OK] Database initialized successfully")

if __name__ == "__main__":
    init_db()
