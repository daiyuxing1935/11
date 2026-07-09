"""学情分析服务"""
import json
from datetime import datetime, timedelta
from database import get_db

def get_user_stats(user_id: int) -> dict:
    """获取用户学习统计数据"""
    conn = get_db()

    # 学习天数（有学习记录的日期数）
    study_days = conn.execute(
        "SELECT COUNT(DISTINCT date) FROM learning_stats WHERE user_id = ?",
        (user_id,)
    ).fetchone()[0]

    # 总做题数
    total_questions = conn.execute(
        "SELECT COALESCE(SUM(questions_done), 0) FROM learning_stats WHERE user_id = ?",
        (user_id,)
    ).fetchone()[0]

    # 平均正确率
    avg_rate = conn.execute(
        "SELECT COALESCE(AVG(correct_rate), 0) FROM learning_stats WHERE user_id = ? AND questions_done > 0",
        (user_id,)
    ).fetchone()[0]

    # 测评统计
    quiz_stats = conn.execute(
        "SELECT COUNT(*) as total, COALESCE(AVG(score * 1.0 / CASE WHEN total = 0 THEN 1 ELSE total END), 0) as avg FROM quiz_sessions WHERE user_id = ? AND status = 'completed'",
        (user_id,)
    ).fetchone()

    # 错题数
    error_count = conn.execute(
        "SELECT COUNT(*) FROM error_questions WHERE user_id = ?", (user_id,)
    ).fetchone()[0]

    # 问答数
    qa_count = conn.execute(
        "SELECT COUNT(*) FROM qa_history WHERE user_id = ?", (user_id,)
    ).fetchone()[0]

    # 周统计
    week_stats = []
    for i in range(6, -1, -1):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        day_stat = conn.execute(
            "SELECT * FROM learning_stats WHERE user_id = ? AND date = ?",
            (user_id, date)
        ).fetchone()
        week_stats.append({
            "date": date,
            "duration": day_stat["study_duration"] if day_stat else 0,
            "questions": day_stat["questions_done"] if day_stat else 0,
            "correct_rate": day_stat["correct_rate"] if day_stat else 0
        })

    # 知识点掌握度
    knowledge_mastery = {}
    from services.diagnosis_service import get_user_knowledge_profile
    profile = get_user_knowledge_profile(user_id)
    knowledge_mastery = {k: v for k, v in list(profile.get("mastery", {}).items())[:12]}

    # 最近学习记录
    recent_records = conn.execute(
        "SELECT * FROM learning_records WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
        (user_id,)
    ).fetchall()

    conn.close()

    return {
        "study_days": study_days,
        "total_study_duration": study_days,  # 兼容旧字段名
        "total_questions": total_questions,
        "avg_correct_rate": round(avg_rate * 100, 1),
        "quiz_count": quiz_stats["total"],
        "quiz_avg_score": round(quiz_stats["avg"] * 100, 1) if quiz_stats["avg"] else 0,
        "error_count": error_count,
        "qa_count": qa_count,
        "knowledge_mastery": knowledge_mastery,
        "weekly_stats": week_stats,
        "recent_records": [dict(r) for r in recent_records]
    }

def get_weekly_report(user_id: int) -> dict:
    """生成周报告"""
    stats = get_user_stats(user_id)

    # 本周学习天数
    week_dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    conn = get_db()
    study_days = 0
    for d in week_dates:
        day = conn.execute(
            "SELECT study_duration FROM learning_stats WHERE user_id = ? AND date = ? AND study_duration > 0",
            (user_id, d)
        ).fetchone()
        if day:
            study_days += 1

    # 本周新错题
    week_errors = conn.execute(
        "SELECT COUNT(*) FROM error_questions WHERE user_id = ? AND created_at >= ?",
        (user_id, week_dates[0])
    ).fetchone()[0]
    conn.close()

    # 趋势判断
    weekly_rates = [d["correct_rate"] for d in stats["weekly_stats"] if d["questions"] > 0]
    trend = "稳定"
    if len(weekly_rates) >= 3:
        recent_avg = sum(weekly_rates[-3:]) / 3
        earlier_avg = sum(weekly_rates[:3]) / 3 if len(weekly_rates) > 3 else recent_avg
        if recent_avg > earlier_avg + 0.05:
            trend = "上升"
        elif recent_avg < earlier_avg - 0.05:
            trend = "下降"

    return {
        "period": f"{week_dates[0]} ~ {week_dates[-1]}",
        "study_days": study_days,
        "total_duration": study_days,
        "avg_correct_rate": stats["avg_correct_rate"],
        "new_errors": week_errors,
        "trend": trend,
        "weekly_stats": stats["weekly_stats"],
        "knowledge_mastery": stats["knowledge_mastery"],
        "suggestions": [
            "本周继续保持学习节奏，重点关注薄弱知识点的巩固",
            "建议每天至少完成1次错题复习",
            "可以尝试高阶难度的题目挑战自己"
        ]
    }

def get_monthly_report(user_id: int) -> dict:
    """生成月报告"""
    conn = get_db()

    # 本月数据
    month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")
    month_stats = conn.execute(
        "SELECT COALESCE(SUM(study_duration), 0) as duration, COALESCE(SUM(questions_done), 0) as questions, COALESCE(AVG(correct_rate), 0) as rate FROM learning_stats WHERE user_id = ? AND date >= ?",
        (user_id, month_start)
    ).fetchone()

    # 本月测评
    month_quizzes = conn.execute(
        "SELECT COUNT(*) as cnt, COALESCE(AVG(score * 1.0 / CASE WHEN total = 0 THEN 1 ELSE total END), 0) as avg FROM quiz_sessions WHERE user_id = ? AND status = 'completed' AND completed_at >= ?",
        (user_id, month_start)
    ).fetchone()

    # 能力成长（对比上月）
    last_month_start = (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")
    last_month_stats = conn.execute(
        "SELECT COALESCE(AVG(correct_rate), 0) as rate FROM learning_stats WHERE user_id = ? AND date >= ? AND date < ?",
        (user_id, last_month_start, month_start)
    ).fetchone()

    # 本月学习天数
    month_study_days = conn.execute(
        "SELECT COUNT(DISTINCT date) FROM learning_stats WHERE user_id = ? AND date >= ?",
        (user_id, month_start)
    ).fetchone()[0]

    conn.close()

    current_rate = round(month_stats["rate"] * 100, 1)
    last_rate = round(last_month_stats["rate"] * 100, 1) if last_month_stats["rate"] else 0
    growth = round(current_rate - last_rate, 1)

    return {
        "period": f"{month_start} ~ {datetime.now().strftime('%Y-%m-%d')}",
        "study_days": month_study_days,
        "total_duration": month_study_days,
        "total_questions": month_stats["questions"] or 0,
        "avg_correct_rate": current_rate,
        "quiz_count": month_quizzes["cnt"] or 0,
        "quiz_avg_score": round(month_quizzes["avg"] * 100, 1) if month_quizzes["avg"] else 0,
        "growth": growth,
        "growth_direction": "up" if growth > 0 else "down" if growth < 0 else "stable"
    }

def record_learning_activity(user_id: int, knowledge_tag: str, action_type: str,
                             duration: int = 0, result: dict = None):
    """记录学习活动"""
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")

    conn.execute(
        "INSERT INTO learning_records (user_id, knowledge_tag, action_type, duration_seconds, result_json) VALUES (?, ?, ?, ?, ?)",
        (user_id, knowledge_tag, action_type, duration, json.dumps(result or {}, ensure_ascii=False))
    )

    # 更新/插入今日统计
    existing = conn.execute(
        "SELECT * FROM learning_stats WHERE user_id = ? AND date = ?",
        (user_id, today)
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE learning_stats SET study_duration = study_duration + ?, questions_done = questions_done + 1 WHERE user_id = ? AND date = ?",
            (duration, user_id, today)
        )
    else:
        conn.execute(
            "INSERT INTO learning_stats (user_id, date, study_duration, questions_done, correct_rate) VALUES (?, ?, ?, ?, ?)",
            (user_id, today, duration, action_type == 'quiz' and 1 or 0, 0)
        )

    conn.commit()
    conn.close()

def get_growth_data(user_id: int) -> dict:
    """获取能力成长轨迹"""
    conn = get_db()
    quizzes = conn.execute(
        "SELECT score, total, completed_at, report_json FROM quiz_sessions WHERE user_id = ? AND status = 'completed' ORDER BY completed_at ASC LIMIT 20",
        (user_id,)
    ).fetchall()
    conn.close()

    growth_points = []
    for q in quizzes:
        rate = q["score"] / q["total"] if q["total"] > 0 else 0
        growth_points.append({
            "date": q["completed_at"][:10] if q["completed_at"] else "",
            "score": q["score"],
            "total": q["total"],
            "rate": round(rate * 100, 1)
        })

    return {
        "growth_points": growth_points,
        "trend": "up" if len(growth_points) >= 2 and growth_points[-1]["rate"] > growth_points[0]["rate"] else "stable"
    }
