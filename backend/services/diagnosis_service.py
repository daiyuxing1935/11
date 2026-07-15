"""学情诊断服务 - 出题/组卷/批改/报告"""
import json
import uuid
from datetime import datetime
from services.ai_service import call_llm, extract_json, extract_json_object, REPORT_PROMPT
from services.question_bank_service import select_questions, load_question_bank
from database import get_db
from config import QUESTION_TYPES, DIFFICULTY_LEVELS, LEARNING_STAGES

def load_knowledge_tags():
    """加载知识点标签库"""
    import os
    from config import KNOWLEDGE_TAGS_PATH
    if not os.path.exists(KNOWLEDGE_TAGS_PATH):
        return []
    with open(KNOWLEDGE_TAGS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_all_tags_flat():
    """获取展平的知识点列表"""
    categories = load_knowledge_tags()
    tags = []
    for cat in categories:
        for tag in cat.get("tags", []):
            tags.append({
                "name": tag["name"],
                "category": cat["category"],
                "difficulty": tag["difficulty"]
            })
    return tags

def get_user_knowledge_profile(user_id: int) -> dict:
    """获取用户学情画像（优化版）

    掌握度计算规则：
    1. 全部标签默认 0.5
    2. 优先从 quiz_sessions.report_json.knowledge_analysis 读取 AI 计算的 mastery
    3. 如果 AI 报告不存在，根据该知识点下历史做题正确率动态计算：
       掌握度 = 答对题数 / 总题数（至少答过 2 题才生效，不足则保持 0.5）
    4. 错题惩罚：同一标签每道错题 -0.03，最低下限 0.1
    5. 分类名→标签名的自动映射
    """
    conn = get_db()

    # --- 读取所有已完成测评的题目和答案 ---
    quizzes = conn.execute(
        "SELECT id, questions_json, answers_json, score, total, report_json"
        " FROM quiz_sessions WHERE user_id = ? AND status = 'completed'"
        " ORDER BY completed_at DESC",
        (user_id,)
    ).fetchall()

    # --- 读取错题 ---
    errors = conn.execute(
        "SELECT knowledge_tag FROM error_questions WHERE user_id = ?",
        (user_id,)
    ).fetchall()

    all_tags = get_all_tags_flat()
    tag_names = [t["name"] for t in all_tags]

    # 分类名 → [标签名] 映射
    category_to_tags = {}
    for t in all_tags:
        cat = t["category"]
        if cat not in category_to_tags:
            category_to_tags[cat] = []
        category_to_tags[cat].append(t["name"])

    # 反过来：标签名 → 分类名
    tag_to_category = {t["name"]: t["category"] for t in all_tags}

    # 初始化掌握度（默认 0 = 无数据）
    mastery = {name: 0.0 for name in tag_names}
    has_data = {name: False for name in tag_names}  # 追踪哪些标签有真实数据

    # ---- 第1步：从 AI 报告提取 mastery ----
    for q in quizzes:
        report = json.loads(q["report_json"]) if q["report_json"] else {}
        ka = report.get("knowledge_analysis", {})
        if not ka:
            continue
        for name, info in ka.items():
            if not isinstance(info, dict):
                continue
            score = round(info.get("mastery", 0.5), 2)
            # 直接匹配标签名
            if name in mastery:
                mastery[name] = score
                has_data[name] = True
            # 分类名 → 映射到该分类下所有标签
            elif name in category_to_tags:
                for tag_name in category_to_tags[name]:
                    mastery[tag_name] = score
                    has_data[tag_name] = True

    # ---- 第2步：从历史做题数据计算正确率 ----
    # 统计各标签的答对数和总题数
    tag_correct = {}   # {tag: correct_count}
    tag_total = {}     # {tag: total_count}
    for q in quizzes:
        try:
            questions = json.loads(q["questions_json"]) if q["questions_json"] else []
            answers = json.loads(q["answers_json"]) if q["answers_json"] else []
        except (json.JSONDecodeError, TypeError):
            continue
        if not questions or not answers:
            continue
        for ans in answers:
            qid = ans.get("question_id", "")
            is_correct = ans.get("is_correct", False)
            # 找到对应题目获取 knowledge_tag
            for qu in questions:
                if qu.get("question_id") == qid:
                    tag = qu.get("knowledge_tag", "")
                    if tag:
                        tag_total[tag] = tag_total.get(tag, 0) + 1
                        if is_correct:
                            tag_correct[tag] = tag_correct.get(tag, 0) + 1
                    break

    # 将做题统计映射到标签 → 更新 mastery
    for tag_name in tag_names:
        total = tag_total.get(tag_name, 0)
        correct = tag_correct.get(tag_name, 0)
        # 分类名也可能作为 knowledge_tag 出现
        if total == 0 and tag_name in category_to_tags:
            for sub_tag in category_to_tags[tag_name]:
                total += tag_total.get(sub_tag, 0)
                correct += tag_correct.get(sub_tag, 0)
        if total >= 1:
            # 只要做过题就标记有数据（即使只有1题）
            if not has_data.get(tag_name, False):
                has_data[tag_name] = True
        if total >= 2:  # 至少 2 题才有统计意义
            rate = correct / total
            # 只在 AI 报告未覆盖时用正确率更新（AI 报告优先）
            if not has_data.get(tag_name, False):
                mastery[tag_name] = round(rate, 2)
                has_data[tag_name] = True
            # AI 报告是分类级数据时，也合并正确率
            elif mastery.get(tag_name, 0.0) < rate:
                mastery[tag_name] = round(rate, 2)

    # ---- 第3步：错题惩罚 ----
    error_counts = {}
    for e in errors:
        tag = e["knowledge_tag"]
        error_counts[tag] = error_counts.get(tag, 0) + 1

    for tag_name in tag_names:
        err_cnt = error_counts.get(tag_name, 0)
        # 分类名也可能出现在错题中
        if err_cnt == 0 and tag_name in category_to_tags:
            for sub_tag in category_to_tags[tag_name]:
                err_cnt += error_counts.get(sub_tag, 0)
        if err_cnt > 0 and has_data.get(tag_name, False):
            penalty = err_cnt * 0.03
            mastery[tag_name] = max(0.0, round(mastery[tag_name] - penalty, 2))

    # ---- 第4步：代码练习完成度 ----
    # 模块号 → 分类名的映射
    module_to_categories = {
        1: ["智能体基础概念"],
        2: ["大模型基座原理", "提示词工程"],
        3: ["智能体算法逻辑"],
        4: ["智能体框架开发"],
        5: ["多智能体应用"],
        6: [],  # 模块六暂无独立知识标签
    }

    # 读取代码提交记录，按模块聚合完成率
    code_rows = conn.execute(
        "SELECT exercise_id, passed, total FROM code_submissions WHERE user_id = ?",
        (user_id,)
    ).fetchall()

    # 按模块统计代码完成情况：{ module_num: (passed_count, total_count) }
    module_code_stats = {i: [0, 0] for i in range(1, 7)}
    import re as _re2
    for row in code_rows:
        eid = row["exercise_id"]
        m = _re2.match(r"(\d+)-\d+", eid)
        if not m:
            continue
        mod_num = int(m.group(1))
        if mod_num not in module_code_stats:
            continue
        module_code_stats[mod_num][0] += 1 if row["passed"] else 0
        module_code_stats[mod_num][1] += 1

    # 将模块完成率映射到知识标签
    code_mastery = {}  # { tag_name: completion_rate }
    code_has_data = {}  # { tag_name: bool }
    for mod_num, cats in module_to_categories.items():
        passed, total = module_code_stats[mod_num]
        if total == 0:
            continue
        rate = round(passed / total, 2)
        for cat in cats:
            if cat in category_to_tags:
                for tag_name in category_to_tags[cat]:
                    code_mastery[tag_name] = rate
                    code_has_data[tag_name] = True

    # 合并代码完成度与做题正确率（各占50%）
    for tag_name in tag_names:
        quiz_score = mastery.get(tag_name, 0.0)
        code_score = code_mastery.get(tag_name)
        has_quiz = has_data.get(tag_name, False)
        has_code = code_has_data.get(tag_name, False)

        if has_quiz and has_code:
            # 两种数据都有 → 各占50%
            mastery[tag_name] = round(quiz_score * 0.5 + code_score * 0.5, 2)
            has_data[tag_name] = True
        elif has_code and not has_quiz:
            # 只有代码数据 → 代码完成度 × 0.8（纯代码没有做题验证，稍微打折）
            mastery[tag_name] = round(code_score * 0.8, 2)
            has_data[tag_name] = True
        # has_quiz only → 保持原值不变

    conn.close()

    # ---- 薄弱点 / 强项 ----
    weak_points_by_category = {}
    for tag, count in error_counts.items():
        cat = tag_to_category.get(tag, tag)
        weak_points_by_category[cat] = weak_points_by_category.get(cat, 0) + count
    weak_points = [cat for cat, _ in sorted(weak_points_by_category.items(), key=lambda x: -x[1])[:5]]

    cat_mastery = {}
    for t in all_tags:
        cat = t["category"]
        if cat not in cat_mastery:
            cat_mastery[cat] = []
        cat_mastery[cat].append(mastery.get(t["name"], 0.0))
    cat_avg_mastery = {cat: round(sum(s) / len(s), 2) for cat, s in cat_mastery.items()}
    strong_points = [cat for cat, _ in sorted(cat_avg_mastery.items(), key=lambda x: -x[1])[:5]]

    return {
        "mastery": mastery,
        "has_data": has_data,
        "weak_points": weak_points,
        "strong_points": strong_points,
        "error_tags": error_counts,
        "quiz_count": len(quizzes)
    }

async def generate_quiz(user_id: int, stage: str = "入门", count: int = 10,
                        focus_knowledge: list = None, question_type: str = None,
                        use_timer: bool = False, timer_minutes: int = 30,
                        knowledge_filter: str = "", exclude_ids: set = None) -> dict:
    """
    生成个性化测评题目 - 从题库中抽题

    Args:
        user_id: 用户ID
        stage: 学习阶段（入门/进阶/高阶）
        count: 题目数量
        focus_knowledge: 重点关注的知识分类
        question_type: 指定题型（暂未使用，题库统一为简答）
        use_timer: 是否启用计时
        timer_minutes: 计时分钟数
    """
    profile = get_user_knowledge_profile(user_id)
    all_tags = get_all_tags_flat()

    # 选取目标知识点（优先薄弱点）
    weak = profile["weak_points"]
    if focus_knowledge:
        target_knowledge = focus_knowledge
    elif weak:
        strong = set(profile["strong_points"][:2])
        target_knowledge = weak[:4] + [t["name"] for t in all_tags if t["name"] not in weak and t["name"] not in strong][:2]
    else:
        target_knowledge = [t["name"] for t in all_tags[:6]]

    avoid_knowledge = profile["strong_points"][:3] if profile["strong_points"] else []

    # 当外部显式指定了focus_knowledge时（如任务做题），跳过avoid避免误排除
    if focus_knowledge:
        avoid_knowledge = []

    # 从题库中选题
    all_questions = select_questions(
        count=count,
        stage=stage,
        focus_knowledge=target_knowledge,
        avoid_topics=avoid_knowledge,
        knowledge_filter=knowledge_filter,
        exclude_ids=exclude_ids
    )

    # 如果题库选题不够，回退说明
    if not all_questions:
        return {
            "error": "题库暂无题目，请检查题库文件是否正确部署",
            "session_id": None,
            "questions": [],
            "total": 0,
            "stage": stage
        }

    # 保存测评会话
    questions_json = json.dumps(all_questions, ensure_ascii=False)
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO quiz_sessions (user_id, stage, questions_json, status) VALUES (?, ?, ?, 'pending')",
        (user_id, stage, questions_json)
    )
    session_id = cursor.lastrowid

    # 记录学习活动
    conn.execute(
        "INSERT INTO learning_records (user_id, knowledge_tag, action_type, result_json) VALUES (?, ?, 'quiz_start', ?)",
        (user_id, "综合", json.dumps({"session_id": session_id, "count": count, "stage": stage}, ensure_ascii=False))
    )

    conn.commit()
    conn.close()

    return {
        "session_id": session_id,
        "questions": all_questions,
        "total": len(all_questions),
        "stage": stage,
        "use_timer": use_timer,
        "timer_minutes": timer_minutes
    }

async def submit_quiz(session_id: int, user_id: int, answers: list) -> dict:
    """提交测评答案并生成报告"""
    conn = get_db()
    session = conn.execute(
        "SELECT * FROM quiz_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id)
    ).fetchone()

    if not session:
        conn.close()
        return {"error": "测评会话不存在"}

    questions = json.loads(session["questions_json"])

    # 批改
    total_score = 0.0
    answer_details = []
    error_questions = []

    for ans in answers:
        qid = ans.get("question_id", "")
        ua = ans.get("user_answer", "").strip()

        question = next((q for q in questions if q.get("question_id") == qid), None)
        if not question:
            continue

        correct_answer = question.get("answer", "").strip()
        qtype = question.get("question_type", "")
        question_text = question.get("question", "")

        # ── 简答题：LLM 语义判分（支持部分得分）──
        if qtype == "简答":
            try:
                q_score, feedback, judge_detail = await _judge_short_answer(
                    ua, correct_answer, question_text,
                    full_score=1, user_id=user_id
                )
            except Exception as e:
                print(f"[submit_quiz] 简答 LLM 判分失败，回退关键词匹配: {e}")
                q_score, feedback, judge_detail = _fallback_keyword_score(ua, correct_answer, 1)

            total_score += q_score
            is_correct = q_score >= 1  # 满分才算全对

            answer_details.append({
                "question_id": qid,
                "user_answer": ua,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "score": q_score,
                "full_score": 1,
                "question_type": qtype,
                "knowledge_tag": question.get("knowledge_tag", ""),
                "difficulty": question.get("difficulty", ""),
                "llm_feedback": feedback,
                "judge_detail": judge_detail,
            })

            if not is_correct:
                error_type = "知识点遗漏" if q_score == 0 else "概念认知偏差"
                error_questions.append({
                    "question_id": qid,
                    "question": question_text,
                    "question_type": qtype,
                    "options": question.get("options", []),
                    "user_answer": ua,
                    "correct_answer": correct_answer,
                    "error_type": error_type,
                    "knowledge_tag": question.get("knowledge_tag", ""),
                    "analysis": question.get("analysis", ""),
                    "difficulty": question.get("difficulty", ""),
                    "option_analysis": question.get("option_analysis", {}),
                    "llm_feedback": feedback,
                })
        else:
            # ── 客观题：沿用原有精确匹配逻辑 ──
            is_correct = _compare_answers(ua, correct_answer, qtype)
            q_score = 1.0 if is_correct else 0.0
            total_score += q_score

            answer_details.append({
                "question_id": qid,
                "user_answer": ua,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "score": q_score,
                "full_score": 1,
                "question_type": qtype,
                "knowledge_tag": question.get("knowledge_tag", ""),
                "difficulty": question.get("difficulty", ""),
            })

            if not is_correct:
                error_type = classify_error_type(ua, correct_answer, qtype)
                error_questions.append({
                    "question_id": qid,
                    "question": question_text,
                    "question_type": qtype,
                    "options": question.get("options", []),
                    "user_answer": ua,
                    "correct_answer": correct_answer,
                    "error_type": error_type,
                    "knowledge_tag": question.get("knowledge_tag", ""),
                    "analysis": question.get("analysis", ""),
                    "difficulty": question.get("difficulty", ""),
                    "option_analysis": question.get("option_analysis", {})
                })

    # 将未作答的题目也加入错题本
    answered_qids = {a.get("question_id", "") for a in answers}
    for question in questions:
        qid = question.get("question_id", "")
        if qid not in answered_qids:
            error_questions.append({
                "question_id": qid,
                "question": question.get("question", ""),
                "question_type": question.get("question_type", ""),
                "options": question.get("options", []),
                "user_answer": "(未作答)",
                "correct_answer": question.get("answer", "").strip(),
                "error_type": "未作答",
                "knowledge_tag": question.get("knowledge_tag", ""),
                "analysis": question.get("analysis", ""),
                "difficulty": question.get("difficulty", ""),
                "option_analysis": question.get("option_analysis", {})
            })
            answer_details.append({
                "question_id": qid,
                "user_answer": "(未作答)",
                "correct_answer": question.get("answer", "").strip(),
                "is_correct": False,
                "question_type": question.get("question_type", ""),
                "knowledge_tag": question.get("knowledge_tag", ""),
                "difficulty": question.get("difficulty", "")
            })

    score = int(round(total_score))
    total = len(questions)
    correct_rate = total_score / total if total > 0 else 0

    # 保存错题到错题本
    for eq in error_questions:
        conn.execute(
            "INSERT INTO error_questions (user_id, session_id, question_data, user_answer, correct_answer, error_type, knowledge_tag) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, session_id, json.dumps(eq, ensure_ascii=False), eq["user_answer"], eq["correct_answer"], eq["error_type"], eq["knowledge_tag"])
        )

    # 生成学情报告
    report = await generate_report(questions, answer_details, correct_rate)

    # 更新测评会话
    conn.execute(
        "UPDATE quiz_sessions SET answers_json = ?, score = ?, total = ?, report_json = ?, status = 'completed', completed_at = ? WHERE id = ?",
        (json.dumps(answer_details, ensure_ascii=False), score, total, json.dumps(report, ensure_ascii=False), datetime.now().isoformat(), session_id)
    )

    # 记录学习行为
    for ad in answer_details:
        conn.execute(
            "INSERT INTO learning_records (user_id, knowledge_tag, action_type, result_json) VALUES (?, ?, 'quiz', ?)",
            (user_id, ad["knowledge_tag"], json.dumps(ad, ensure_ascii=False))
        )

    # 根据题型估算学习时长（分钟）
    type_time_map = {"单选": 0.5, "填空": 1, "简答": 2, "判断": 0.5, "代码实操": 3, "多选": 0.5}
    estimated_duration = sum(type_time_map.get(q.get("question_type", "简答"), 2) for q in questions)

    # 更新每日学习统计
    today = datetime.now().strftime("%Y-%m-%d")
    existing_stats = conn.execute(
        "SELECT * FROM learning_stats WHERE user_id = ? AND date = ?",
        (user_id, today)
    ).fetchone()

    if existing_stats:
        # 更新已有记录：累加做题数和学习时长，重新计算正确率
        old_questions = existing_stats["questions_done"] or 0
        old_duration = existing_stats["study_duration"] or 0
        old_correct = int(old_questions * (existing_stats["correct_rate"] or 0))
        new_questions = old_questions + total
        new_correct = old_correct + score
        new_rate = new_correct / new_questions if new_questions > 0 else 0
        conn.execute(
            "UPDATE learning_stats SET study_duration = ?, questions_done = ?, correct_rate = ? WHERE user_id = ? AND date = ?",
            (old_duration + int(estimated_duration), new_questions, round(new_rate, 3), user_id, today)
        )
    else:
        # 新建记录
        new_rate = score / total if total > 0 else 0
        conn.execute(
            "INSERT INTO learning_stats (user_id, date, study_duration, questions_done, correct_rate) VALUES (?, ?, ?, ?, ?)",
            (user_id, today, int(estimated_duration), total, round(new_rate, 3))
        )

    conn.commit()
    conn.close()

    return {
        "session_id": session_id,
        "score": score,
        "total": total,
        "correct_rate": round(correct_rate * 100, 1),
        "answer_details": answer_details,
        "error_questions": error_questions,
        "report": report
    }

# ── LLM 语义判分 Prompt ────────────────────────────────────────
# 设计思路：
#   1. 让 LLM 先拆解标准答案为若干"得分要点"，每个要点是一个独立的知识点或判断维度
#   2. 逐一比对学生的回答是否"覆盖"了每个要点
#   3. "覆盖"的定义是语义等价，不是字面匹配——同义词、语序颠倒、口语化转述都算命中
#   4. 只有概念理解错误、完全没提到该要点时才判定为未命中
#   5. 得分 = 命中要点数 ÷ 总要点数 × 题目满分，结果取整
#   6. 要求 LLM 必须返回 JSON，方便程序解析；增加格式约束防止多余文本
#   7. 阈值：当学生回答与标准要点的语义相似度 > 70% 时判定命中

SHORT_ANSWER_JUDGE_PROMPT = """你是一位严格但公正的阅卷老师。你的任务是评判学生简答题的得分。

【评分规则 — 务必遵守】
1. 先把"标准答案"拆解为若干个独立的得分要点（core_points），每个要点 10 字以上、表达一个完整的知识点
2. 逐一检查学生的回答是否覆盖了每个要点
3. "覆盖"的判定标准（重要！）：
   - 学生用自己的话转述、同义词替换、语序调整 → 只要核心意思一致 → 算命中
   - 学生回答中有该要点的关键信息，即使表述不完整 → 语义相似度 > 70% → 算命中
   - 只有学生完全没提到该要点、或理解完全错误 → 才算未命中
4. 不要因为学生用词不够专业、句子不够通顺而扣分
5. 最终得分 = 命中要点数 ÷ 总要点数 × 题目满分（{full_score} 分），结果四舍五入取整数

【输出格式 — 必须严格遵守】
只输出一个 JSON 对象，不要有任何其他文字：
{{
  "core_points": ["要点1：xxx", "要点2：xxx"],
  "hit_points": ["命中的要点原文"],
  "score": 整数得分,
  "feedback": "简短评语（30字内），指出命中了哪些要点、哪些缺失"
}}

【题目】
{question_text}

【标准答案】
{correct_answer}

【学生回答】
{user_answer}

请立即输出 JSON："""


async def _judge_short_answer(user_answer: str, correct_answer: str,
                               question_text: str = "", full_score: int = 1,
                               user_id: int = 1) -> tuple[int, str, dict]:
    """
    LLM 语义判分——简答题专用。

    返回:
        (score, feedback, detail)
        - score: 0 ~ full_score 之间的整数
        - feedback: 简短评语
        - detail: {"core_points": [...], "hit_points": [...], "raw_score": int}
    """
    if not user_answer or not user_answer.strip():
        return 0, "未作答", {"core_points": [], "hit_points": [], "raw_score": 0}

    if not correct_answer or not correct_answer.strip():
        return full_score, "", {"core_points": [], "hit_points": [], "raw_score": full_score}

    # 极短答案（< 3 字）回退到快速判断
    ua = user_answer.strip()
    if len(ua) < 3:
        ca = correct_answer.strip()
        if ua in ca or ca in ua:
            return full_score, "答案正确", {"core_points": [], "hit_points": [], "raw_score": full_score}
        return 0, "答案过短，无法判定为正确", {"core_points": [], "hit_points": [], "raw_score": 0}

    prompt = SHORT_ANSWER_JUDGE_PROMPT.format(
        question_text=question_text or "（见上文）",
        correct_answer=correct_answer,
        user_answer=user_answer,
        full_score=full_score,
    )

    try:
        raw = await asyncio.wait_for(
            call_llm(user_id, [{"role": "user", "content": prompt}],
                     temperature=0.1, max_tokens=600),
            timeout=20.0
        )
    except asyncio.TimeoutError:
        # 超时 → 回退到关键词匹配
        return _fallback_keyword_score(user_answer, correct_answer, full_score)
    except Exception as e:
        print(f"[_judge_short_answer] LLM 调用失败: {e}")
        return _fallback_keyword_score(user_answer, correct_answer, full_score)

    # 解析 JSON
    try:
        result = extract_json_object(raw)
    except Exception:
        # 尝试从原始回复中提取 JSON
        import re as _re2
        m = _re2.search(r'\{[^{}]*"core_points"[^{}]*\}', raw, _re2.DOTALL)
        if m:
            try:
                result = json.loads(m.group())
            except Exception:
                return _fallback_keyword_score(user_answer, correct_answer, full_score)
        else:
            return _fallback_keyword_score(user_answer, correct_answer, full_score)

    # 校验并规范化
    core_points = result.get("core_points", [])
    hit_points = result.get("hit_points", [])
    raw_score = result.get("score", 0)
    feedback = result.get("feedback", "")

    # 合理性校验：得分不能超过满分
    if isinstance(raw_score, (int, float)):
        score = max(0, min(full_score, int(round(raw_score))))
    else:
        score = 0

    # 如果没有提取到要点，回退
    if not core_points:
        return _fallback_keyword_score(user_answer, correct_answer, full_score)

    detail = {
        "core_points": core_points,
        "hit_points": hit_points,
        "raw_score": score,
    }

    return score, feedback, detail


def _fallback_keyword_score(user_answer: str, correct_answer: str, full_score: int) -> tuple:
    """
    兜底方案：LLM 不可用时用关键词匹配估算分数。
    返回 (score, feedback, detail)
    """
    import re as _re3
    ca_keywords = _re3.findall(r'[一-鿿]{2,}', correct_answer)
    if not ca_keywords:
        return 0, "", {"core_points": [], "hit_points": [], "raw_score": 0}

    matches = sum(1 for kw in ca_keywords if kw in user_answer)
    ratio = matches / len(ca_keywords)
    score = int(round(ratio * full_score))
    return score, f"（自动判分：关键词匹配率 {int(ratio * 100)}%）", {
        "core_points": ca_keywords,
        "hit_points": [kw for kw in ca_keywords if kw in user_answer],
        "raw_score": score,
    }


# 为了在同步上下文中使用，需要 asyncio
import asyncio


def _compare_answers(user_answer: str, correct_answer: str, question_type: str) -> bool:
    """灵活的答案比较——简答题已迁移至 LLM 语义判分，此函数仅处理客观题"""
    if not user_answer or not correct_answer:
        return False

    ua = user_answer.strip().lower()
    ca = correct_answer.strip().lower()

    # 完全一致
    if ua == ca:
        return True

    # 填空题：更严格的匹配（短答案需要精确匹配）
    if question_type == "填空":
        import re
        ua_clean = re.sub(r'[^\w一-鿿]', '', ua)
        ca_clean = re.sub(r'[^\w一-鿿]', '', ca)
        if ua_clean == ca_clean:
            return True
        if len(ca_clean) >= 3 and (ca_clean in ua_clean or ua_clean in ca_clean):
            return True
        return False

    # 对于选择题/判断题，只要答案核心内容匹配即可
    if question_type in ["单选", "多选", "判断"]:
        import re
        ua_clean = re.sub(r'\s+', '', ua)
        ca_clean = re.sub(r'\s+', '', ca)
        return ua_clean == ca_clean

    # 简答题 → 由 LLM 语义判分（_judge_short_answer），此处不再用关键词匹配
    # 如果在 submit_quiz 中未调用 LLM（回退路径），则用原有关键词逻辑兜底
    if question_type == "简答":
        import re
        ca_keywords = re.findall(r'[一-鿿]{2,}', correct_answer)
        if ca_keywords:
            matches = sum(1 for kw in ca_keywords if kw in ua)
            if matches >= len(ca_keywords) * 0.5:
                return True
        return False

    return False


def classify_error_type(user_answer: str, correct_answer: str, question_type: str) -> str:
    """分类错误类型"""
    if not user_answer:
        return "知识点遗漏"
    if question_type == "代码实操":
        return "代码语法失误"
    if question_type == "填空":
        if len(user_answer.strip()) < 1:
            return "知识点遗漏"
        if len(user_answer.strip()) < len(correct_answer.strip()) * 0.5:
            return "知识点遗漏"
        return "概念认知偏差"
    if question_type == "简答":
        if len(user_answer) < len(correct_answer) * 0.3:
            return "知识点遗漏"
        return "概念认知偏差"
    if question_type in ["单选", "多选", "判断"]:
        return "概念认知偏差"
    return "审题理解偏差"

async def generate_report(questions: list, answer_details: list, correct_rate: float) -> dict:
    """生成学情诊断报告"""
    # 按知识点统计
    knowledge_stats = {}
    for ad in answer_details:
        tag = ad.get("knowledge_tag", "未分类")
        if tag not in knowledge_stats:
            knowledge_stats[tag] = {"correct": 0, "total": 0}
        knowledge_stats[tag]["total"] += 1
        if ad["is_correct"]:
            knowledge_stats[tag]["correct"] += 1

    # 按能力维度统计
    ability_map = {
        "概念理解": ["智能体基础概念"],
        "原理辨析": ["大模型基座原理"],
        "算法逻辑": ["智能体算法逻辑"],
        "代码实操": ["智能体框架开发"],
        "应用分析": ["多智能体应用", "提示词工程"]
    }

    ability_stats = {}
    for ability, categories in ability_map.items():
        total_c = 0
        total_t = 0
        for ad in answer_details:
            tag = ad.get("knowledge_tag", "")
            qcat = ""
            for q in questions:
                if q.get("question_id") == ad["question_id"]:
                    break
            # 通过knowledge_tag匹配所属category
            for cat in categories:
                all_tags = get_all_tags_flat()
                for t in all_tags:
                    if t["name"] == tag and t["category"] in categories:
                        total_t += 1
                        if ad["is_correct"]:
                            total_c += 1
                        break
        if total_t == 0:
            ability_stats[ability] = {"score": 0.5, "comment": "暂无数据"}
        else:
            score = total_c / total_t
            level = "优秀" if score >= 0.9 else "良好" if score >= 0.7 else "一般" if score >= 0.5 else "薄弱"
            ability_stats[ability] = {"score": round(score, 2), "comment": f"{level}，{total_c}/{total_t}正确"}

    # 构建知识分析
    knowledge_analysis = {}
    for tag, stats in knowledge_stats.items():
        m = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
        level = "优秀" if m >= 0.9 else "良好" if m >= 0.7 else "一般" if m >= 0.5 else "薄弱" if m >= 0.3 else "盲区"
        knowledge_analysis[tag] = {
            "mastery": round(m, 2),
            "level": level,
            "comment": f"{stats['correct']}/{stats['total']}题正确，{level}水平"
        }

    # 找出薄弱点和优势点
    weak_points = [tag for tag, s in knowledge_stats.items()
                   if s["correct"] / s["total"] < 0.5] if knowledge_stats else []
    strong_points = [tag for tag, s in knowledge_stats.items()
                     if s["correct"] / s["total"] >= 0.8] if knowledge_stats else []

    # 利用AI生成综合评语
    quiz_summary = f"共{len(answer_details)}题，正确{int(correct_rate * len(answer_details))}题，正确率{round(correct_rate*100, 1)}%"
    suggestions = [
        "建议重点复习薄弱知识点，结合错题本进行针对性练习",
        "已掌握内容可进行拔高拓展，挑战更高难度题目",
        "实操类题目建议多动手编码，配合智能体框架实战练习"
    ]

    if weak_points:
        suggestions.insert(0, f"重点攻坚：{'、'.join(weak_points[:3])}")

    return {
        "overall_assessment": f"本次测评{quiz_summary}。{'表现优秀，基础扎实！' if correct_rate >= 0.8 else '表现良好，继续努力！' if correct_rate >= 0.6 else '还有提升空间，针对性加强薄弱环节。'}",
        "knowledge_analysis": knowledge_analysis,
        "ability_analysis": ability_stats,
        "weak_points": weak_points,
        "strong_points": strong_points,
        "error_summary": f"主要错误集中在{'、'.join(weak_points[:3]) if weak_points else '无明显薄弱环节'}",
        "study_suggestions": suggestions,
        "next_focus": weak_points[0] if weak_points else "全面巩固，适当拔高"
    }

async def get_diagnosis_history(user_id: int) -> list:
    """获取诊断历史"""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, stage, score, total, status, created_at, completed_at FROM quiz_sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

async def get_report(session_id: int, user_id: int) -> dict:
    """获取单次测评报告"""
    conn = get_db()
    session = conn.execute(
        "SELECT * FROM quiz_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id)
    ).fetchone()
    conn.close()
    if not session:
        return {}
    return {
        "session_id": session["id"],
        "score": session["score"],
        "total": session["total"],
        "correct_rate": round(session["score"] / session["total"] * 100, 1) if session["total"] > 0 else 0,
        "stage": session["stage"],
        "report": json.loads(session["report_json"]) if session["report_json"] else {},
        "created_at": session["created_at"],
        "completed_at": session["completed_at"]
    }
