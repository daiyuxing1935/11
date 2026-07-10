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
    """获取用户学情画像"""
    conn = get_db()
    # 统计答题记录
    records = conn.execute(
        "SELECT knowledge_tag, action_type, result_json FROM learning_records WHERE user_id = ? ORDER BY created_at DESC LIMIT 200",
        (user_id,)
    ).fetchall()
    # 统计错题
    errors = conn.execute(
        "SELECT knowledge_tag, error_type FROM error_questions WHERE user_id = ? ORDER BY created_at DESC LIMIT 100",
        (user_id,)
    ).fetchall()
    # 获取测评历史
    quizzes = conn.execute(
        "SELECT report_json FROM quiz_sessions WHERE user_id = ? AND status = 'completed' ORDER BY completed_at DESC LIMIT 5",
        (user_id,)
    ).fetchall()
    conn.close()

    all_tags = get_all_tags_flat()
    tag_names = [t["name"] for t in all_tags]

    # 构建 分类→标签名 映射，用于将报告的类别级数据映射到具体标签
    category_to_tags = {}
    for t in all_tags:
        cat = t["category"]
        if cat not in category_to_tags:
            category_to_tags[cat] = []
        category_to_tags[cat].append(t["name"])

    # 初始化掌握度
    mastery = {name: 0.5 for name in tag_names}  # 默认0.5

    # 从历史报告更新掌握度
    for q in quizzes:
        report = json.loads(q["report_json"]) if q["report_json"] else {}
        ka = report.get("knowledge_analysis", {})
        for name, info in ka.items():
            if not isinstance(info, dict):
                continue
            score = info.get("mastery", 0.5)
            # 直接匹配标签名
            if name in mastery:
                mastery[name] = score
            # 如果是分类名（如"智能体基础概念"），映射到该分类下所有标签
            elif name in category_to_tags:
                for tag_name in category_to_tags[name]:
                    mastery[tag_name] = score

    # 统计薄弱点（按分类聚合）
    error_tags = {}
    for e in errors:
        tag = e["knowledge_tag"]
        error_tags[tag] = error_tags.get(tag, 0) + 1

    # 按分类聚合薄弱点
    weak_points_by_category = {}
    for tag, count in error_tags.items():
        # 找到该标签所属的分类
        found_cat = None
        for t in all_tags:
            if t["name"] == tag:
                found_cat = t["category"]
                break
        if not found_cat:
            # 如果tag本身就是分类名
            found_cat = tag
        weak_points_by_category[found_cat] = weak_points_by_category.get(found_cat, 0) + count

    weak_points = [cat for cat, count in sorted(weak_points_by_category.items(), key=lambda x: -x[1])[:5]]
    # 强项取 mastery 较高的分类
    cat_mastery = {}
    for t in all_tags:
        cat = t["category"]
        if cat not in cat_mastery:
            cat_mastery[cat] = []
        cat_mastery[cat].append(mastery.get(t["name"], 0.5))

    cat_avg_mastery = {cat: sum(scores)/len(scores) for cat, scores in cat_mastery.items()}
    strong_points = [cat for cat, m in sorted(cat_avg_mastery.items(), key=lambda x: -x[1])[:5]]

    return {
        "mastery": mastery,
        "weak_points": weak_points,
        "strong_points": strong_points,
        "error_tags": error_tags,
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
    correct_count = 0
    answer_details = []
    error_questions = []

    for ans in answers:
        qid = ans.get("question_id", "")
        ua = ans.get("user_answer", "").strip()

        question = next((q for q in questions if q.get("question_id") == qid), None)
        if not question:
            continue

        correct_answer = question.get("answer", "").strip()
        # 使用更灵活的答案比较：忽略大小写和空白差异，支持部分匹配
        is_correct = _compare_answers(ua, correct_answer, question.get("question_type", ""))

        if is_correct:
            correct_count += 1
        else:
            # 判断错误类型
            error_type = classify_error_type(ua, correct_answer, question.get("question_type", ""))
            error_questions.append({
                "question_id": qid,
                "question": question.get("question", ""),
                "question_type": question.get("question_type", ""),
                "options": question.get("options", []),
                "user_answer": ua,
                "correct_answer": correct_answer,
                "error_type": error_type,
                "knowledge_tag": question.get("knowledge_tag", ""),
                "analysis": question.get("analysis", ""),
                "difficulty": question.get("difficulty", ""),
                "option_analysis": question.get("option_analysis", {})
            })

        answer_details.append({
            "question_id": qid,
            "user_answer": ua,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "question_type": question.get("question_type", ""),
            "knowledge_tag": question.get("knowledge_tag", ""),
            "difficulty": question.get("difficulty", "")
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

    score = correct_count
    total = len(questions)
    correct_rate = score / total if total > 0 else 0

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

def _compare_answers(user_answer: str, correct_answer: str, question_type: str) -> bool:
    """灵活的答案比较，支持忽略大小写/空白差异"""
    if not user_answer or not correct_answer:
        return False

    ua = user_answer.strip().lower()
    ca = correct_answer.strip().lower()

    # 完全一致
    if ua == ca:
        return True

    # 填空题：更严格的匹配（短答案需要精确匹配）
    if question_type == "填空":
        # 去除标点符号后比较
        import re
        ua_clean = re.sub(r'[^\w一-鿿]', '', ua)
        ca_clean = re.sub(r'[^\w一-鿿]', '', ca)
        if ua_clean == ca_clean:
            return True
        # 允许单字差异（如"通义晓蜜" vs "通义晓蜜大模型"）
        if len(ca_clean) >= 3 and (ca_clean in ua_clean or ua_clean in ca_clean):
            return True
        return False

    # 对于简答题，检查用户答案是否包含正确答案的关键内容
    # 提取正确答案中的关键内容（去除非中文/英文的噪音字符）
    import re
    # 提取中文字符序列作为关键词
    ca_keywords = re.findall(r'[一-鿿]{2,}', correct_answer)
    if ca_keywords:
        matches = sum(1 for kw in ca_keywords if kw in ua)
        if matches >= len(ca_keywords) * 0.5:  # 至少50%关键词匹配
            return True

    # 对于选择题/判断题，只要答案核心内容匹配即可
    if question_type in ["单选", "多选", "判断"]:
        ua_clean = re.sub(r'\s+', '', ua)
        ca_clean = re.sub(r'\s+', '', ca)
        return ua_clean == ca_clean

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
