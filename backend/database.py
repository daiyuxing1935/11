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

    # RAG 知识库文档追踪表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rag_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_path TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_title TEXT DEFAULT '',
            source_module TEXT DEFAULT '',
            doc_hash TEXT NOT NULL,
            chunk_count INTEGER DEFAULT 0,
            char_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            error_msg TEXT DEFAULT '',
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_source ON rag_documents(source_path)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_status ON rag_documents(status)")

    # 数据库迁移
    _run_migration(conn, "error_questions", "session_id INTEGER", "错题表迁移: 添加 session_id 列")
    _run_migration(conn, "user_llm_config", "image_api_key TEXT DEFAULT ''", "LLM配置表迁移: 添加 image_api_key 列")
    _run_migration(conn, "user_llm_config", "embedding_provider TEXT DEFAULT ''", "LLM配置表迁移: 添加 embedding_provider 列")
    _run_migration(conn, "user_llm_config", "embedding_api_key TEXT DEFAULT ''", "LLM配置表迁移: 添加 embedding_api_key 列")
    _run_migration(conn, "user_llm_config", "embedding_model TEXT DEFAULT 'text-embedding-v3'", "LLM配置表迁移: 添加 embedding_model 列")
    _run_migration(conn, "learning_stats", "mastery_detail_json TEXT DEFAULT '{}'", "学习统计表迁移: 添加 mastery_detail_json 列")
    _run_migration(conn, "qa_history", "rag_sources_json TEXT DEFAULT ''", "QA历史表迁移: 添加 rag_sources_json 列")

    # 习题评测元数据表 — 存储每道题的锁定代码/目标函数/测试用例
    conn.execute("""
        CREATE TABLE IF NOT EXISTS exercise_test_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercise_id TEXT UNIQUE NOT NULL,
            exercise_type TEXT DEFAULT 'function',
            target_function TEXT DEFAULT '',
            locked_code TEXT DEFAULT '',
            guide_comment TEXT DEFAULT '# 请在此处实现代码',
            test_cases_json TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()

    # 代码提交评测记录表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS code_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exercise_id TEXT NOT NULL,
            code TEXT NOT NULL,
            passed INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0,
            score REAL DEFAULT 0,
            results_json TEXT DEFAULT '[]',
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()

    # 电子书表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pdf_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            cover TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    _run_migration(conn, "pdf_books", "cover TEXT DEFAULT NULL", "电子书表迁移: 添加封面字段")

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

    # Seed bundled PDF metadata without replacing the persistent database.
    # The PDF binaries are version-controlled, while the live SQLite file is
    # intentionally not; merge missing rows by username and filename.
    try:
        import json as _json

        _pdf_seed_path = os.path.join(os.path.dirname(__file__), "data", "pdf_books_seed.json")
        _pdf_dir = os.path.join(os.path.dirname(__file__), "data", "pdfs")
        _pdf_count = 0
        if os.path.exists(_pdf_seed_path):
            with open(_pdf_seed_path, "r", encoding="utf-8") as _f:
                _pdf_seed = _json.load(_f)
            for _book in _pdf_seed:
                _user = conn.execute(
                    "SELECT id FROM users WHERE username = ?", (_book.get("username", ""),)
                ).fetchone()
                _filename = os.path.basename(str(_book.get("filename", "")))
                _pdf_path = os.path.join(_pdf_dir, _filename)
                if not _user or not _filename or not os.path.isfile(_pdf_path):
                    continue
                _existing = conn.execute(
                    "SELECT 1 FROM pdf_books WHERE user_id = ? AND filename = ?",
                    (_user["id"], _filename),
                ).fetchone()
                if _existing:
                    continue
                _cover = _book.get("cover")
                if _cover and not os.path.isfile(os.path.join(_pdf_dir, "covers", os.path.basename(_cover))):
                    _cover = None
                conn.execute(
                    "INSERT INTO pdf_books "
                    "(user_id, filename, original_name, file_size, cover, created_at) "
                    "VALUES (?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))",
                    (
                        _user["id"],
                        _filename,
                        _book.get("original_name") or _filename,
                        os.path.getsize(_pdf_path),
                        _cover,
                        _book.get("created_at"),
                    ),
                )
                _pdf_count += 1
            conn.commit()
        if _pdf_count:
            print(f"[OK] Imported {_pdf_count} bundled PDF book records")
    except Exception as e:
        print(f"[WARN] Bundled PDF metadata import failed: {e}")

    # Seed knowledge_tags from JSON (only if table is empty to avoid duplicates)
    try:
        _tags_path = os.path.join(os.path.dirname(__file__), "data", "knowledge_tags.json")
        _tag_exist = conn.execute("SELECT COUNT(*) FROM knowledge_tags").fetchone()[0]
        if _tag_exist == 0 and os.path.exists(_tags_path):
            import json as _json
            with open(_tags_path, "r", encoding="utf-8") as _f:
                _tag_data = _json.load(_f)
            _tag_count = 0
            for _cat in _tag_data:
                _cat_name = _cat.get("category", "")
                for _tag in _cat.get("tags", []):
                    _tag_name = _tag.get("name", "")
                    if not _tag_name:
                        continue
                    conn.execute(
                        "INSERT INTO knowledge_tags (name, category, description) VALUES (?, ?, ?)",
                        (_tag_name, _cat_name, _tag.get("description", ""))
                    )
                    _tag_count += 1
            conn.commit()
            print(f"[OK] 已导入 {_tag_count} 条知识标签到数据库")
    except Exception as e:
        print(f"[WARN] 知识标签导入失败: {e}")

    # Seed exercise_test_metadata from exercises_processed.json (only if empty)
    try:
        _exist = conn.execute("SELECT COUNT(*) FROM exercise_test_metadata").fetchone()[0]
        if _exist == 0:
            _ex_path = os.path.join(os.path.dirname(__file__), "data", "exercises_processed.json")
            if os.path.exists(_ex_path):
                import json as _json, re as _re
                with open(_ex_path, "r", encoding="utf-8") as _f:
                    _exercises = _json.load(_f)
                _ex_count = 0
                for _ex in _exercises:
                    _raw = _ex.get("skeleton_code", "") or _ex.get("starter_code", "")
                    _funcs = _re.findall(r'def\s+(\w+)\s*\(', _raw)
                    _target = ""
                    for _fn in _funcs:
                        if not _fn.startswith("_") and _fn != "__init__":
                            _target = _fn
                            break
                    if not _target and _funcs:
                        _target = _funcs[0]
                    _cls = _re.search(r'class\s+(\w+)', _raw)
                    _etype = "class_method" if _cls else "function"
                    _guide = f"# 请在此处实现 {_target}() 函数功能" if _target else "# 请在此处编写代码"
                    conn.execute(
                        "INSERT OR IGNORE INTO exercise_test_metadata "
                        "(exercise_id, exercise_type, target_function, locked_code, guide_comment, test_cases_json) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (_ex["id"], _etype, _target, _raw, _guide, "[]")
                    )
                    _ex_count += 1
                conn.commit()
                print(f"[OK] 已导入 {_ex_count} 条习题评测元数据")
    except Exception as e:
        print(f"[WARN] 习题元数据导入失败: {e}")

    conn.commit()
    conn.close()

    # 自动导入 generated_images 目录中的 SVG 文件到数据库
    _import_svgs_to_db()

    print("[OK] Database initialized successfully")


def _import_svgs_to_db():
    """将 generated_images 目录中的 SVG 文件自动导入 SQLite，确保首次运行即有所需配图"""
    import os as _os
    images_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data", "generated_images")
    if not _os.path.isdir(images_dir):
        return

    conn = get_db()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS generated_images ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, "
        "prompt_hash TEXT NOT NULL, prompt_text TEXT NOT NULL, "
        "svg_content TEXT, file_path TEXT, provider TEXT DEFAULT 'llm-svg', "
        "created_at TEXT)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_img_h ON generated_images(prompt_hash)")

    imported = 0
    for fn in _os.listdir(images_dir):
        if not fn.endswith('.svg'):
            continue
        h = fn.replace('.svg', '')
        # 跳过已存在的
        existing = conn.execute(
            "SELECT 1 FROM generated_images WHERE prompt_hash = ? AND svg_content IS NOT NULL",
            (h,)
        ).fetchone()
        if existing:
            continue
        fpath = _os.path.join(images_dir, fn)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                svg = f.read()
            conn.execute(
                "INSERT OR REPLACE INTO generated_images "
                "(user_id, prompt_hash, prompt_text, svg_content, file_path, provider, created_at) "
                "VALUES (1, ?, ?, ?, ?, 'bundled', datetime('now'))",
                (h, f"bundled {h[:16]}", svg, fpath)
            )
            imported += 1
        except Exception:
            pass

    if imported > 0:
        print(f"[OK] 已导入 {imported} 张 SVG 配图到数据库")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
