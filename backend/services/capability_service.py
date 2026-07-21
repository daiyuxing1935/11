"""编程能力真实性验证闭环。

代码通过只代表功能正确；学生还需要完成基于本人代码的答辩和故障修复，
系统才会把该练习标记为“能力已验证”。过程事件只用于形成学习证据，
不会输出作弊概率，也不会单独作为惩罚依据。
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from database import get_db
from services.judge_service import get_flagship_exercise, is_flagship_exercise, judge_submission


DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "exercises_processed.json"
MATERIAL_INDEX_CANDIDATES = (
    Path(__file__).resolve().parents[2] / "learning_materials" / "index.json",
    Path("/learning_materials/index.json"),
)
CODE_START = "# ==========你的代码开始=========="
CODE_END = "# ==========你的代码结束=========="


def _loads(raw: Any, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return default


def _exercise(exercise_id: str) -> dict:
    flagship = get_flagship_exercise(exercise_id)
    if flagship:
        return flagship
    try:
        with DATA_PATH.open("r", encoding="utf-8") as file:
            for item in json.load(file):
                if item.get("id") == exercise_id:
                    return item
    except Exception:
        pass
    return {"id": exercise_id, "title": exercise_id, "module": "编程实践"}


def _session_dict(row) -> dict:
    data = dict(row)
    for column, default in (
        ("defense_questions_json", []),
        ("defense_answers_json", []),
        ("report_json", {}),
    ):
        data[column.removesuffix("_json")] = _loads(data.pop(column, None), default)
    data["verified"] = bool(data.get("verified"))
    return data


def _owned_session(user_id: int, session_id: int):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM capability_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()
    conn.close()
    if not row:
        raise ValueError("能力验证会话不存在或无权访问")
    return row


def start_session(user_id: int, exercise_id: str, force_new: bool = False) -> dict:
    """创建或恢复一条尚未完成的能力验证会话。"""
    if not is_flagship_exercise(exercise_id):
        raise ValueError("该旧题已停止能力验证，待按旗舰题标准重制")
    conn = get_db()
    if not force_new:
        row = conn.execute(
            """SELECT * FROM capability_sessions
               WHERE user_id = ? AND exercise_id = ?
               ORDER BY id DESC LIMIT 1""",
            (user_id, exercise_id),
        ).fetchone()
        if row:
            conn.close()
            return _session_dict(row)

    ex = _exercise(exercise_id)
    cursor = conn.execute(
        """INSERT INTO capability_sessions
           (user_id, exercise_id, exercise_title, knowledge_tag, status)
           VALUES (?, ?, ?, ?, 'coding')""",
        (user_id, exercise_id, ex.get("title", ""), ex.get("module", "")),
    )
    session_id = cursor.lastrowid
    conn.execute(
        """INSERT INTO capability_events (session_id, user_id, event_type, payload_json)
           VALUES (?, ?, 'session_start', ?)""",
        (session_id, user_id, json.dumps({"exercise_id": exercise_id}, ensure_ascii=False)),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM capability_sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return _session_dict(row)


def record_events(user_id: int, session_id: int, events: list[dict]) -> dict:
    _owned_session(user_id, session_id)
    allowed = {"edit", "paste", "run", "submit", "hint", "answer_view", "focus_return"}
    cleaned = []
    for event in events[:100]:
        event_type = str(event.get("type", ""))[:40]
        if event_type not in allowed:
            continue
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        # 不保存每次按键和完整剪贴板，只保留粗粒度数量证据。
        safe_payload = {
            str(key)[:40]: value
            for key, value in payload.items()
            if key in {"delta", "length", "passed", "failed", "duration", "source", "visible"}
            and isinstance(value, (str, int, float, bool, type(None)))
        }
        cleaned.append((session_id, user_id, event_type, json.dumps(safe_payload, ensure_ascii=False)))

    if cleaned:
        conn = get_db()
        conn.executemany(
            """INSERT INTO capability_events (session_id, user_id, event_type, payload_json)
               VALUES (?, ?, ?, ?)""",
            cleaned,
        )
        conn.commit()
        conn.close()
    return {"recorded": len(cleaned)}


def _run_embedded_tests(code: str, timeout: int = 15) -> dict:
    """运行题目自带测试驱动。与现有实验室行为保持一致。"""
    try:
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, "main.py")
            with open(source, "w", encoding="utf-8") as file:
                file.write(code)
            proc = subprocess.run(
                [os.environ.get("PYTHON_PATH", "python"), source],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                cwd=tmp,
            )
        output = proc.stdout or ""
        passed_count = output.count("[PASS]")
        failed_count = output.count("[FAIL]")
        return {
            "passed": proc.returncode == 0 and passed_count > 0 and failed_count == 0,
            "passed_count": passed_count,
            "failed_count": failed_count,
            "compile_error": "" if proc.returncode == 0 else (proc.stderr or "运行失败")[-800:],
            "output": output[-1200:],
        }
    except subprocess.TimeoutExpired:
        return {"passed": False, "passed_count": 0, "failed_count": 1, "compile_error": "执行超时", "output": ""}
    except Exception as exc:
        return {"passed": False, "passed_count": 0, "failed_count": 1, "compile_error": str(exc), "output": ""}


def _judge_exercise_code(exercise_id: str, code: str) -> dict:
    """能力闭环与普通提交共用同一判题源，防止阶段之间标准漂移。"""
    if is_flagship_exercise(exercise_id):
        result = judge_submission(exercise_id, code)
        result["failed_count"] = max(result.get("total", 0) - result.get("passed_count", 0), 0)
        result["output"] = ""
        return result
    return _run_embedded_tests(code)


def _user_region(code: str) -> tuple[str, int, int]:
    start = code.find(CODE_START)
    end = code.find(CODE_END)
    if start >= 0 and end > start:
        region_start = start + len(CODE_START)
        return code[region_start:end], region_start, end
    main = code.find("if __name__")
    end = main if main > 0 else len(code)
    return code[:end], 0, end


def _code_identifiers(code: str) -> list[str]:
    region, _, _ = _user_region(code)
    try:
        tree = ast.parse(region)
    except Exception:
        return []
    names = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.append(node.id)
    return list(dict.fromkeys(name for name in names if len(name) > 1))[:8]


def _authoritative_source(exercise: dict) -> dict:
    """从现有课程知识库索引中检索与练习最接近的权威条目。

    这条确定性关键词检索也是向量服务不可用时的 RAG 降级路径，确保答辩始终
    有真实来源，而不是让模型凭空生成“依据”。
    """
    index_data = {}
    for path in MATERIAL_INDEX_CANDIDATES:
        try:
            if path.exists():
                index_data = json.loads(path.read_text(encoding="utf-8"))
                break
        except Exception:
            continue

    modules = index_data.get("modules", {}) if isinstance(index_data, dict) else {}
    module_name = str(exercise.get("module", ""))
    module_prefix = re.match(r"模块[一二三四五六]", module_name)
    candidates = {}
    for name, entries in modules.items():
        if module_prefix and str(name).startswith(module_prefix.group(0)):
            candidates.update(entries if isinstance(entries, dict) else {})
    if not candidates:
        for entries in modules.values():
            if isinstance(entries, dict):
                candidates.update(entries)

    query = f"{exercise.get('title', '')}{exercise.get('description', '')}"
    query_chars = set(re.sub(r"\s|[·：—（）()、]", "", query))
    best_name = "课程知识库"
    best_path = ""
    best_score = -1
    for name, relative_path in candidates.items():
        name_chars = set(re.sub(r"\s|[·：—（）()、]", "", str(name)))
        score = len(query_chars & name_chars)
        if str(name) in query:
            score += 20
        if score > best_score:
            best_name, best_path, best_score = str(name), str(relative_path), score
    return {
        "label": f"{best_name} · 课程知识库",
        "path": best_path,
    }


def _defense_questions(code: str, exercise: dict) -> list[dict]:
    region, _, _ = _user_region(code)
    identifiers = _code_identifiers(code)
    target = identifiers[0] if identifiers else exercise.get("title", "本实现")
    source = _authoritative_source(exercise)
    questions = [
        {
            "id": "q1",
            "prompt": f"请用自己的话说明 `{target}` 接收什么输入、经过哪些关键步骤、最终返回什么。",
            "focus": "输入—处理—输出链路",
            "rubric": [["输入", "参数"], ["步骤", "处理", "逻辑"], ["输出", "返回", "结果"]],
            "source": source["label"],
            "source_path": source["path"],
        }
    ]

    if "for " in region or "while " in region:
        questions.append({
            "id": "q2", "prompt": "代码中的循环何时结束？如果输入为空或规模扩大，会出现什么行为？",
            "focus": "循环与边界条件",
            "rubric": [["结束", "终止", "条件"], ["空", "边界"], ["复杂度", "规模", "性能"]],
            "source": source["label"], "source_path": source["path"],
        })
    elif "if " in region:
        questions.append({
            "id": "q2", "prompt": "请选择一个关键条件分支，说明它为什么存在；去掉这个分支会导致哪个具体用例失败？",
            "focus": "分支设计与反事实解释",
            "rubric": [["条件", "分支"], ["因为", "用于", "避免"], ["失败", "错误", "用例"]],
            "source": source["label"], "source_path": source["path"],
        })
    elif "class " in region:
        questions.append({
            "id": "q2", "prompt": "这个类保存了哪些状态？方法调用前后，哪个状态会发生变化，为什么？",
            "focus": "对象状态变化",
            "rubric": [["状态", "属性"], ["调用", "方法"], ["变化", "更新"]],
            "source": source["label"], "source_path": source["path"],
        })
    else:
        questions.append({
            "id": "q2", "prompt": "你的实现依赖了哪一个最关键的设计选择？请给出一种替代方案并比较取舍。",
            "focus": "设计选择与权衡",
            "rubric": [["选择", "使用"], ["替代", "另一种"], ["优点", "缺点", "取舍"]],
            "source": source["label"], "source_path": source["path"],
        })

    questions.append({
        "id": "q3",
        "prompt": "如果需求增加一个此前没有覆盖的异常输入，你会在哪一层增加保护？请说明修改位置和验证方法。",
        "focus": "迁移与验证策略",
        "rubric": [["异常", "边界", "校验"], ["修改", "增加", "位置"], ["测试", "验证", "用例"]],
        "source": source["label"],
        "source_path": source["path"],
    })
    return questions


def _replace_region(code: str, region: str, start: int, end: int) -> str:
    return code[:start] + region + code[end:]


def _mutation_candidates(code: str) -> list[tuple[str, str]]:
    region, start, end = _user_region(code)
    candidates: list[tuple[str, str]] = []

    # 优先制造“可解释的语义故障”，且逐个验证确实能让测试失败。
    for match in list(re.finditer(r"(?m)^(\s*)return\s+([^\n#]+)", region))[:5]:
        expression = match.group(2).strip()
        if expression in {"None", "False"} or expression.endswith(("{", "[", "(")):
            continue
        broken_region = region[:match.start()] + f"{match.group(1)}return None" + region[match.end():]
        candidates.append((_replace_region(code, broken_region, start, end), "一个关键返回值被破坏。请根据测试现象定位原因，恢复正确的数据流。"))

    operator_rules = [(">=", ">"), ("<=", "<"), ("==", "!="), (" + ", " - ")]
    for old, new in operator_rules:
        if old in region:
            broken_region = region.replace(old, new, 1)
            candidates.append((_replace_region(code, broken_region, start, end), "一个边界或运算规则发生了变化。请定位导致用例失败的设计条件并修复。"))

    # 没有合适表达式时，注入一个显式运行故障，确保每道题都有修复环节。
    function_match = re.search(r"(?m)^(\s*)def\s+\w+\([^\n]*\):\s*$", region)
    if function_match:
        indent = function_match.group(1) + "    "
        insert_at = function_match.end()
        broken_region = region[:insert_at] + f"\n{indent}raise RuntimeError('状态转换失败')" + region[insert_at:]
        candidates.append((_replace_region(code, broken_region, start, end), "实现中出现了一个阻断正常执行的故障。请结合终端输出定位并修复。"))
    return candidates


def _build_mutation(exercise_id: str, code: str) -> tuple[str, str]:
    for mutated, description in _mutation_candidates(code):
        if not _judge_exercise_code(exercise_id, mutated)["passed"]:
            return mutated, description
    return code, "请为当前实现补充一个异常输入保护，并确保全部测试仍然通过。"


def mark_code_passed(user_id: int, session_id: int, code: str) -> dict:
    row = _owned_session(user_id, session_id)
    evaluation = _judge_exercise_code(row["exercise_id"], code)
    if not evaluation["passed"]:
        raise ValueError("服务端复核未通过，不能进入能力答辩")

    exercise = _exercise(row["exercise_id"])
    questions = _defense_questions(code, exercise)
    mutation_code, mutation_description = _build_mutation(row["exercise_id"], code)
    now = datetime.now().isoformat()
    conn = get_db()
    conn.execute(
        """UPDATE capability_sessions
           SET status = 'defense_pending', original_code = ?, code_score = 100,
               defense_questions_json = ?, mutation_code = ?, mutation_description = ?,
               code_passed_at = ?
           WHERE id = ? AND user_id = ?""",
        (code, json.dumps(questions, ensure_ascii=False), mutation_code, mutation_description, now, session_id, user_id),
    )
    conn.execute(
        "INSERT INTO capability_events (session_id, user_id, event_type, payload_json) VALUES (?, ?, 'code_passed', ?)",
        (session_id, user_id, json.dumps({"passed_count": evaluation["passed_count"]}, ensure_ascii=False)),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM capability_sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return _session_dict(updated)


def _answer_score(answer: str, question: dict, identifiers: list[str]) -> tuple[int, list[str], list[str]]:
    normalized = answer.lower().strip()
    hit_labels = []
    missing_labels = []
    rubric = question.get("rubric", [])
    for group in rubric:
        if any(str(keyword).lower() in normalized for keyword in group):
            hit_labels.append("/".join(group))
        else:
            missing_labels.append("/".join(group))
    coverage = len(hit_labels) / max(len(rubric), 1)
    detail = min(len(answer.strip()) / 80, 1.0)
    specificity = 1.0 if any(identifier.lower() in normalized for identifier in identifiers) else 0.0
    score = round((coverage * 0.65 + detail * 0.25 + specificity * 0.10) * 100)
    return score, hit_labels, missing_labels


def submit_defense(user_id: int, session_id: int, answers: list[dict], ai_usage: str) -> dict:
    row = _owned_session(user_id, session_id)
    questions = _loads(row["defense_questions_json"], [])
    answer_map = {str(item.get("question_id")): str(item.get("answer", "")) for item in answers}
    identifiers = _code_identifiers(row["original_code"] or "")
    details = []
    for question in questions:
        answer = answer_map.get(question.get("id"), "")
        score, hits, missing = _answer_score(answer, question, identifiers)
        details.append({
            "question_id": question.get("id"),
            "prompt": question.get("prompt"),
            "answer": answer,
            "score": score,
            "hit_points": hits,
            "missing_points": missing,
        })
    score = round(sum(item["score"] for item in details) / max(len(details), 1))
    passed = score >= 60 and all(item["answer"].strip() for item in details)
    status = "repair_pending" if passed else "defense_pending"
    conn = get_db()
    conn.execute(
        """UPDATE capability_sessions
           SET defense_answers_json = ?, defense_score = ?, ai_usage = ?, status = ?
           WHERE id = ? AND user_id = ?""",
        (json.dumps(details, ensure_ascii=False), score, ai_usage[:40], status, session_id, user_id),
    )
    conn.execute(
        "INSERT INTO capability_events (session_id, user_id, event_type, payload_json) VALUES (?, ?, 'defense_submit', ?)",
        (session_id, user_id, json.dumps({"score": score, "passed": passed}, ensure_ascii=False)),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM capability_sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    data = _session_dict(updated)
    data["defense_passed"] = passed
    return data


def _process_evidence(conn, session_id: int, started_at: str, ai_usage: str) -> tuple[int, dict]:
    rows = conn.execute(
        "SELECT event_type, payload_json FROM capability_events WHERE session_id = ?",
        (session_id,),
    ).fetchall()
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["event_type"]] = counts.get(row["event_type"], 0) + 1
    try:
        elapsed_minutes = max(0, (datetime.now() - datetime.fromisoformat(started_at)).total_seconds() / 60)
    except Exception:
        elapsed_minutes = 0
    score = 35
    score += min(counts.get("edit", 0) * 3, 20)
    score += min(counts.get("run", 0) * 5, 20)
    score += 10 if elapsed_minutes >= 2 else round(elapsed_minutes * 5)
    score += 10 if ai_usage else 0
    score += 5 if counts.get("submit", 0) else 0
    evidence = {
        "edit_snapshots": counts.get("edit", 0),
        "paste_events": counts.get("paste", 0),
        "run_attempts": counts.get("run", 0),
        "hint_views": counts.get("hint", 0) + counts.get("answer_view", 0),
        "elapsed_minutes": round(elapsed_minutes, 1),
        "ai_usage": ai_usage or "未声明",
        "note": "过程数据只用于说明证据完整度，不用于判定作弊。",
    }
    return min(score, 100), evidence


def submit_repair(user_id: int, session_id: int, code: str, explanation: str) -> dict:
    row = _owned_session(user_id, session_id)
    if row["status"] != "repair_pending":
        raise ValueError("请先通过代码答辩再进入故障修复")

    evaluation = _judge_exercise_code(row["exercise_id"], code)
    explanation = explanation.strip()
    explanation_score = min(20, round(len(explanation) / 4))
    repair_score = (80 if evaluation["passed"] else 0) + explanation_score
    repair_passed = evaluation["passed"] and explanation_score >= 8

    conn = get_db()
    if not repair_passed:
        conn.execute(
            """UPDATE capability_sessions SET repair_code = ?, repair_explanation = ?, repair_score = ?
               WHERE id = ? AND user_id = ?""",
            (code, explanation, repair_score, session_id, user_id),
        )
        conn.execute(
            "INSERT INTO capability_events (session_id, user_id, event_type, payload_json) VALUES (?, ?, 'repair_submit', ?)",
            (session_id, user_id, json.dumps({"passed": False, "score": repair_score}, ensure_ascii=False)),
        )
        conn.commit()
        conn.close()
        return {"repair_passed": False, "repair_score": repair_score, "evaluation": evaluation}

    process_score, evidence = _process_evidence(conn, session_id, row["started_at"], row["ai_usage"] or "")
    code_score = 100
    defense_score = float(row["defense_score"] or 0)
    total_score = round(code_score * 0.25 + defense_score * 0.25 + repair_score * 0.40 + process_score * 0.10)
    report = {
        "verified": True,
        "verdict": "能力已验证",
        "summary": "代码正确、原理答辩和故障修复均已形成可复核证据。",
        "dimensions": {
            "代码正确性": code_score,
            "原理理解": round(defense_score),
            "故障修复与迁移": repair_score,
            "过程证据完整度": process_score,
        },
        "process_evidence": evidence,
        "defense_evidence": _loads(row["defense_answers_json"], []),
        "knowledge_sources": list(dict.fromkeys(
            question.get("source_path")
            for question in _loads(row["defense_questions_json"], [])
            if question.get("source_path")
        )),
        "repair_evidence": {
            "description": row["mutation_description"],
            "explanation": explanation,
            "tests_passed": True,
        },
        "total_score": total_score,
        "next_step": "尝试修改输入约束或替换一种实现策略，再比较两种方案的取舍。",
    }
    now = datetime.now().isoformat()
    conn.execute(
        """UPDATE capability_sessions
           SET repair_code = ?, repair_explanation = ?, repair_score = ?, process_score = ?,
               total_score = ?, verified = 1, status = 'verified', report_json = ?, completed_at = ?
           WHERE id = ? AND user_id = ?""",
        (code, explanation, repair_score, process_score, total_score,
         json.dumps(report, ensure_ascii=False), now, session_id, user_id),
    )
    # 只有完成整套闭环，代码提交才进入掌握度统计。
    conn.execute(
        """UPDATE code_submissions SET verified = 1
           WHERE id = (
               SELECT id FROM code_submissions
               WHERE user_id = ? AND exercise_id = ? AND passed = 1
               ORDER BY id DESC LIMIT 1
           )""",
        (user_id, row["exercise_id"]),
    )
    conn.execute(
        "INSERT INTO capability_events (session_id, user_id, event_type, payload_json) VALUES (?, ?, 'verified', ?)",
        (session_id, user_id, json.dumps({"total_score": total_score}, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()
    return {"repair_passed": True, "verified": True, "report": report, "evaluation": evaluation}


def get_session(user_id: int, session_id: int) -> dict:
    return _session_dict(_owned_session(user_id, session_id))
