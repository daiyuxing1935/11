"""
统一数据库连接管理

- 设置环境变量 DATABASE_URL 时使用 PostgreSQL
- 未设置时使用 SQLite（完全向后兼容）
- psycopg2 连接自动转换 ? 占位符为 %s
- INSERT OR IGNORE → ON CONFLICT DO NOTHING
- INSERT OR REPLACE → ON CONFLICT ... DO UPDATE
"""
import json
import os
import sqlite3
import re
from config import DATABASE_PATH

_DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_TYPE = "postgresql" if _DATABASE_URL else "sqlite"

# PostgreSQL 相关导入（延迟导入以兼容无 psycopg2 的环境）
_psycopg2 = None
_psycopg2_extras = None


def _ensure_psycopg2():
    global _psycopg2, _psycopg2_extras
    if _psycopg2 is None:
        import psycopg2 as _pg
        import psycopg2.extras as _pg_extras
        _psycopg2 = _pg
        _psycopg2_extras = _pg_extras

# ── 表 → 冲突列映射（用于 INSERT OR IGNORE/REPLACE → ON CONFLICT） ──
# 格式: { "table_name": ["col1" (, "col2")] }
# 多数表冲突列为 PK "id"；有 UNIQUE 约束的表列出实际冲突列
TABLE_CONFLICT_MAP = {
    # 单列自增主键（INSERT 不指定 id 时无冲突风险，指定时冲突在 id）
    "users":                      ["id"],           # 另: username UNIQUE
    "knowledge_tags":             ["id"],
    "quiz_sessions":              ["id"],
    "error_questions":            ["id"],
    "qa_history":                 ["id"],
    "learning_paths":             ["id"],
    "daily_tasks":                ["id"],
    "learning_records":           ["id"],
    "user_resources":             ["id"],
    "qa_feedback":                ["id"],
    "qa_patterns":                ["id"],
    "conversation_sessions":      ["id"],
    "conversation_messages":      ["id"],
    "rag_documents":              ["id"],
    "tutorial_documents":         ["id"],
    "code_submissions":           ["id"],
    "capability_sessions":        ["id"],
    "capability_events":          ["id"],
    "pdf_books":                  ["id"],
    # 有 UNIQUE 约束的表 — 冲突列不是 id
    "user_llm_config":            ["user_id"],      # user_id UNIQUE NOT NULL
    "learning_stats":             ["user_id", "date"],
    "user_memory_facts":          ["user_id", "category", "fact_key"],
    "knowledge_mastery":          ["user_id", "knowledge_tag"],
    "exercise_test_metadata":     ["exercise_id"],  # exercise_id UNIQUE NOT NULL
    "generated_images":           ["prompt_hash"],  # prompt_hash UNIQUE NOT NULL
    # 助教系统的表（共享 PG 库时也会遇到）
    "lesson_plans":               ["id"],
    "homework_grades":            ["id"],
    "exercise_batches":           ["id"],
    "materials":                  ["id"],
    "questions":                  ["id"],
    "insight_reports":            ["id"],
    "teaching_aux":               ["id"],
    "llm_call_logs":              ["id"],
    "audit_logs":                 ["id"],
    "plan_snapshots":             ["id"],
    "agent_workflows":            ["id"],
    "project_registry":           ["project_id"],
}


def get_db():
    """
    获取数据库连接。

    SQLite:  返回原生 sqlite3.Connection（row_factory=Row）
    PostgreSQL: 返回 _PGWrapper，透明转换 ? → %s，兼容现有代码
    """
    if DB_TYPE == "postgresql":
        _ensure_psycopg2()
        _patch_real_dict_row()
        conn = _psycopg2.connect(_DATABASE_URL)
        conn.cursor_factory = _psycopg2_extras.RealDictCursor
        return _PGWrapper(conn)
    else:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn


# RealDictRow monkey-patch：支持 row[0] 整数索引（兼容 sqlite3.Row 用法）
def _patch_real_dict_row():
    """给 RealDictRow 添加整数索引支持，只需调用一次"""
    _ensure_psycopg2()
    _RealDictRow = _psycopg2_extras.RealDictRow
    if hasattr(_RealDictRow, '_patched_compat'):
        return
    _RealDictRow._patched_compat = True
    _orig_getitem = _RealDictRow.__getitem__
    def _patched_getitem(self, key):
        if isinstance(key, int):
            cols = list(self.keys())
            if 0 <= key < len(cols):
                return _orig_getitem(self, cols[key])
            raise IndexError(f"column index out of range")
        return _orig_getitem(self, key)
    _RealDictRow.__getitem__ = _patched_getitem


class _CompatRow(dict):
    """兼容行：dict['col'] + row[0] 索引，兼容 sqlite3.Row 的 API"""

    def __getitem__(self, key):
        if isinstance(key, int):
            cols = list(self.keys())
            if 0 <= key < len(cols):
                return dict.__getitem__(self, cols[key])
            raise IndexError(f"column index {key} out of range")
        return dict.__getitem__(self, key)

    def get(self, key, default=None):
        if isinstance(key, int):
            cols = list(self.keys())
            if 0 <= key < len(cols):
                return dict.get(self, cols[key], default)
            return default
        return dict.get(self, key, default)

    def keys(self):
        return super().keys()

    def values(self):
        return super().values()

    def __iter__(self):
        return iter(self.values())


class _DummyCursor:
    """当 INSERT OR IGNORE 被 UniqueViolation 抑制时返回的空游标"""

    def fetchone(self):
        return None

    def fetchall(self):
        return []

    def fetchmany(self, size=None):
        return []

    @property
    def rowcount(self):
        return 0

    @property
    def lastrowid(self):
        return None

    def close(self):
        pass

    def __iter__(self):
        return iter([])


_INSERT_IGNORE_RE = re.compile(
    r"INSERT\s+OR\s+IGNORE\s+INTO\s+(\w+)\s*\(([^)]+)\)",
    re.IGNORECASE,
)
_INSERT_REPLACE_RE = re.compile(
    r"INSERT\s+OR\s+REPLACE\s+INTO\s+(\w+)\s*\(([^)]+)\)",
    re.IGNORECASE,
)


class _PGWrapper:
    """
    psycopg2 连接的薄包装层，兼容 sqlite3.Connection 常用接口。

    自动处理:
    - ? 占位符 → %s
    - INSERT OR IGNORE → INSERT ... ON CONFLICT (pk) DO NOTHING
    - INSERT OR REPLACE → INSERT ... ON CONFLICT (pk) DO UPDATE SET ...
    - date('now') → CURRENT_DATE
    - datetime('now') → NOW()
    - PRAGMA foreign_keys = ON → 空操作（PG 默认开启）
    - UniqueViolation 兜底捕获（对未映射的表）
    """

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=None):
        # 在翻译前检测 OR IGNORE / OR REPLACE 语义
        is_ignore = bool(_INSERT_IGNORE_RE.search(sql))
        is_replace = bool(_INSERT_REPLACE_RE.search(sql))

        sql = self._translate_sql(sql)

        # 对可能产生唯一约束冲突的语句，使用 SAVEPOINT 隔离
        if is_ignore or is_replace:
            _ensure_psycopg2()
            pg_errors = _psycopg2.errors
            cur = self._conn.cursor()
            cur.execute("SAVEPOINT _pgw_sp")
            try:
                if params is not None:
                    cur.execute(sql, params)
                else:
                    cur.execute(sql)
                cur.execute("RELEASE SAVEPOINT _pgw_sp")
                return cur
            except pg_errors.UniqueViolation:
                cur.execute("ROLLBACK TO SAVEPOINT _pgw_sp")
                self._conn.commit()  # 提交回滚后的状态
                if is_ignore:
                    return _DummyCursor()
                # REPLACE 语义: 冲突时 DELETE 旧行 + INSERT 新行
                # 实现为 DELETE + INSERT（需要知道冲突列，这里只能抛出）
                raise RuntimeError(
                    f"INSERT OR REPLACE failed: no conflict target known. "
                    f"Add table to TABLE_CONFLICT_MAP in db.py. SQL: {sql[:120]}"
                ) from None
            except Exception:
                cur.execute("ROLLBACK TO SAVEPOINT _pgw_sp")
                self._conn.commit()
                raise

        cur = self._conn.cursor()
        try:
            if params is not None:
                cur.execute(sql, params)
            else:
                cur.execute(sql)
        except Exception:
            self._conn.rollback()
            raise
        return cur

    def executescript(self, sql):
        """模拟 sqlite3 的 executescript：拆分 ; 逐条执行"""
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt and not stmt.startswith("--"):
                self.execute(stmt)
        self._conn.commit()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    # psycopg2 连接透传方法（某些代码可能直接调用）
    def cursor(self):
        return self._conn.cursor()

    # 允许直接访问底层连接（高级用法）
    @property
    def raw(self):
        return self._conn

    # ── 内部方法 ──

    @staticmethod
    def _translate_sql(sql):
        """转换 SQLite 特有语法到 PostgreSQL"""
        # PRAGMA（仅 SQLite）
        if sql.strip().upper().startswith("PRAGMA"):
            return "SELECT 1"  # 无害空操作

        # CREATE INDEX IF NOT EXISTS（预建表属主是 postgres，app_user 无 alter 权限）
        if re.match(r"CREATE\s+INDEX\s+IF\s+NOT\s+EXISTS", sql.strip(), re.IGNORECASE):
            return "SELECT 1"

        # ── DDL 翻译：SQLite → PostgreSQL ──
        # AUTOINCREMENT → SERIAL（PG 不支持 AUTOINCREMENT）
        sql = re.sub(
            r"INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT",
            "SERIAL PRIMARY KEY",
            sql,
            flags=re.IGNORECASE,
        )

        # ── INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING ──
        m_ignore = _INSERT_IGNORE_RE.search(sql)
        if m_ignore:
            table = m_ignore.group(1).lower()
            cols_str = m_ignore.group(2)
            conflict_cols = TABLE_CONFLICT_MAP.get(table, ["id"])
            conflict_clause = ", ".join(conflict_cols)
            # 移除 "OR IGNORE"
            sql = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", sql, count=1, flags=re.IGNORECASE)
            # 追加 ON CONFLICT ... DO NOTHING（在语句末尾，分号之前）
            sql = _append_on_conflict(sql, f"ON CONFLICT ({conflict_clause}) DO NOTHING")

        # ── INSERT OR REPLACE → INSERT ... ON CONFLICT ... DO UPDATE ──
        m_replace = _INSERT_REPLACE_RE.search(sql)
        if m_replace:
            table = m_replace.group(1).lower()
            cols_str = m_replace.group(2)
            conflict_cols = TABLE_CONFLICT_MAP.get(table, ["id"])
            conflict_clause = ", ".join(conflict_cols)

            # 解析列名列表
            col_names = [c.strip() for c in cols_str.split(",")]

            # 生成 SET 子句（排除冲突列本身）
            set_items = []
            for c in col_names:
                stripped = c.strip()
                if stripped and stripped not in conflict_cols:
                    set_items.append(f"{stripped}=EXCLUDED.{stripped}")

            # 移除 "OR REPLACE"
            sql = re.sub(r"INSERT\s+OR\s+REPLACE\s+INTO", "INSERT INTO", sql, count=1, flags=re.IGNORECASE)

            if set_items:
                set_clause = ", ".join(set_items)
                update_clause = f"ON CONFLICT ({conflict_clause}) DO UPDATE SET {set_clause}"
            else:
                # 所有列都是冲突列 → 无所谓，DO NOTHING
                update_clause = f"ON CONFLICT ({conflict_clause}) DO NOTHING"
            sql = _append_on_conflict(sql, update_clause)

        # SQLite 函数 → PostgreSQL 函数
        sql = sql.replace("date('now')", "CURRENT_DATE")
        sql = sql.replace("datetime('now')", "NOW()")

        # ? 占位符 → %s（跳过字符串字面量中的 ?）
        sql = _translate_placeholders(sql)

        return sql


def _append_on_conflict(sql, clause):
    """在 SQL 语句末尾（分号之前）追加 ON CONFLICT 子句"""
    sql = sql.rstrip()
    if sql.endswith(";"):
        return sql[:-1].rstrip() + " " + clause + ";"
    else:
        return sql + " " + clause


def _translate_placeholders(sql):
    """将 SQLite 的 ? 占位符替换为 PostgreSQL 的 %s，跳过引号内的 ?"""
    result = []
    in_single = False
    in_double = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if ch == "'" and not in_double:
            in_single = not in_single
            result.append(ch)
        elif ch == '"' and not in_single:
            in_double = not in_double
            result.append(ch)
        elif ch == "?" and not in_single and not in_double:
            result.append("%s")
        else:
            result.append(ch)
        i += 1
    return "".join(result)


def is_postgresql():
    """检查当前是否使用 PostgreSQL"""
    return DB_TYPE == "postgresql"


def json_load(val):
    """兼容 SQLite TEXT 和 PG JSONB：dict/list 直接返回，字符串则 json.loads"""
    if val is None or val == '':
        return None
    if isinstance(val, (dict, list)):
        return val
    return json.loads(val)
