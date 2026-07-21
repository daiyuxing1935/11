"""Flagship private judge regression and bypass tests."""

import unittest

from services.judge_service import judge_submission


CORRECT_SOLUTION = '''
PRIORITIES = ("low", "normal", "high", "urgent")
SLA = {"low": 480, "normal": 120, "high": 30, "urgent": 15}

def dispatch_ticket(ticket, agents, now_minutes):
    if not isinstance(ticket, dict) or not isinstance(agents, list):
        raise ValueError("ticket 和 agents 结构非法")
    required_ticket = ("id", "category", "priority", "vip", "created_at")
    if not all(key in ticket for key in required_ticket):
        raise ValueError("ticket 缺少必填字段")
    if not isinstance(ticket["id"], str) or not ticket["id"]:
        raise ValueError("工单 id 非法")
    if not isinstance(ticket["category"], str) or not ticket["category"]:
        raise ValueError("category 非法")
    if ticket["priority"] not in PRIORITIES or not isinstance(ticket["vip"], bool):
        raise ValueError("优先级或 vip 非法")
    created_at = ticket["created_at"]
    if (not isinstance(created_at, int) or isinstance(created_at, bool) or created_at < 0
            or not isinstance(now_minutes, int) or isinstance(now_minutes, bool)
            or now_minutes < created_at):
        raise ValueError("时间字段非法")

    priority_index = PRIORITIES.index(ticket["priority"])
    if ticket["vip"]:
        priority_index += 1
    if now_minutes - created_at >= 60:
        priority_index += 1
    effective_priority = PRIORITIES[min(priority_index, len(PRIORITIES) - 1)]

    eligible = []
    for item in agents:
        required_agent = ("id", "skills", "online", "active_cases", "capacity")
        if not isinstance(item, dict) or not all(key in item for key in required_agent):
            raise ValueError("客服结构非法")
        if not isinstance(item["id"], str) or not item["id"] or not isinstance(item["skills"], list):
            raise ValueError("客服 id 或 skills 非法")
        active, capacity = item["active_cases"], item["capacity"]
        if (not isinstance(item["online"], bool)
                or not isinstance(active, int) or isinstance(active, bool) or active < 0
                or not isinstance(capacity, int) or isinstance(capacity, bool) or capacity <= 0):
            raise ValueError("客服状态或容量非法")
        if item["online"] and ticket["category"] in item["skills"] and active < capacity:
            eligible.append(item)

    selected = min(eligible, key=lambda item: (item["active_cases"] / item["capacity"], item["id"])) if eligible else None
    return {
        "ticket_id": ticket["id"],
        "status": "assigned" if selected else "queued",
        "agent_id": selected["id"] if selected else None,
        "effective_priority": effective_priority,
        "sla_minutes": SLA[effective_priority],
        "reason": "matched_skill_and_capacity" if selected else "no_eligible_agent",
    }
'''


class FlagshipJudgeTest(unittest.TestCase):
    def test_correct_business_solution_passes_every_private_scenario(self):
        result = judge_submission("7-1", CORRECT_SOLUTION)
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["passed_count"], 10)
        self.assertEqual(result["judge_mode"], "server_private_cases")

    def test_printing_pass_marker_cannot_bypass_judge(self):
        result = judge_submission("7-1", 'print("[PASS]" * 100)')
        self.assertFalse(result["passed"])
        self.assertIn("模块顶层", result["compile_error"])

    def test_import_and_file_access_are_rejected(self):
        for source in ("import os\n", "def dispatch_ticket(a, b, c):\n    return open('x')\n"):
            with self.subTest(source=source):
                result = judge_submission("7-1", source)
                self.assertFalse(result["passed"])
                self.assertIn("安全检查未通过", result["compile_error"])

    def test_using_raw_case_count_instead_of_load_ratio_fails(self):
        wrong = CORRECT_SOLUTION.replace(
            '(item["active_cases"] / item["capacity"], item["id"])',
            '(item["active_cases"], item["id"])',
        )
        result = judge_submission("7-1", wrong)
        self.assertFalse(result["passed"])
        failed = [item["description"] for item in result["results"] if not item["passed"]]
        self.assertIn("按负载率而非绝对工单数选择", failed)

    def test_mutating_inputs_fails_even_when_return_value_looks_right(self):
        wrong = CORRECT_SOLUTION.replace(
            "    priority_index = PRIORITIES.index(ticket[\"priority\"])",
            "    ticket[\"audited\"] = True\n    priority_index = PRIORITIES.index(ticket[\"priority\"])",
        )
        result = judge_submission("7-1", wrong)
        self.assertFalse(result["passed"])
        failed = [item["description"] for item in result["results"] if not item["passed"]]
        self.assertIn("输入对象保持不变", failed)


if __name__ == "__main__":
    unittest.main()
