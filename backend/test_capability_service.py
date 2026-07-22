"""能力验证闭环的最小集成测试。"""

import os
import tempfile
import unittest

import database
from services import capability_service
from test_judge_service import CORRECT_SOLUTION


class CapabilityLoopTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database.DATABASE_PATH = os.path.join(self.temp_dir.name, "capability-test.db")
        database.init_db()
        conn = database.get_db()
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, nickname) VALUES ('capability-test', 'x', '测试学生')"
        )
        self.user_id = cursor.lastrowid
        conn.commit()
        conn.close()

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def correct_code():
        return CORRECT_SOLUTION

    def test_code_defense_repair_report_loop(self):
        session = capability_service.start_session(self.user_id, "1-1")
        capability_service.record_events(self.user_id, session["id"], [
            {"type": "edit", "payload": {"delta": 42, "length": 900}},
            {"type": "run", "payload": {"passed": False, "failed": 1}},
            {"type": "run", "payload": {"passed": True, "failed": 0}},
            {"type": "submit", "payload": {"source": "code"}},
        ])

        passed = capability_service.mark_code_passed(self.user_id, session["id"], self.correct_code())
        self.assertEqual(passed["status"], "defense_pending")
        self.assertEqual(len(passed["defense_questions"]), 3)
        self.assertIn("source", passed["defense_questions"][0])
        self.assertNotEqual(passed["mutation_code"], self.correct_code())

        answers = [
            {"question_id": "q1", "answer": "build_chat_messages 的输入参数是系统提示和用户文本；处理步骤是类型校验、清理空白和构造消息，输出并返回消息列表。"},
            {"question_id": "q2", "answer": "if 分支用于拒绝空字符串和错误类型；去掉后非法输入不会失败，私有错误用例会失败。"},
            {"question_id": "q3", "answer": "面对异常或边界输入，我会在入口校验层增加保护，明确修改位置，并补充测试用例验证 ValueError 和返回结构。"},
        ]
        defense = capability_service.submit_defense(
            self.user_id, session["id"], answers, "AI提供了提示"
        )
        self.assertTrue(defense["defense_passed"])
        self.assertEqual(defense["status"], "repair_pending")

        conn = database.get_db()
        conn.execute(
            """INSERT INTO code_submissions
               (user_id, exercise_id, code, passed, total, score, verified)
               VALUES (?, '1-1', ?, 1, 4, 100, 0)""",
            (self.user_id, self.correct_code()),
        )
        conn.commit()
        conn.close()

        repaired = capability_service.submit_repair(
            self.user_id,
            session["id"],
            self.correct_code(),
            "故障根因是关键返回值被改成空值，导致测试读取不到字典；我恢复了返回表达式并重新运行全部用例。",
        )
        self.assertTrue(repaired["verified"])
        self.assertEqual(repaired["report"]["verdict"], "能力已验证")
        self.assertGreaterEqual(repaired["report"]["total_score"], 60)

        conn = database.get_db()
        row = conn.execute(
            "SELECT verified FROM code_submissions WHERE user_id = ? AND exercise_id = '1-1'",
            (self.user_id,),
        ).fetchone()
        conn.close()
        self.assertEqual(row["verified"], 1)


if __name__ == "__main__":
    unittest.main()
