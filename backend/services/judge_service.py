"""Server-owned judge for the flagship business exercise.

The browser receives the contract and starter code, never these scenarios.  This
is an application-level isolation boundary, not a hardened multi-tenant sandbox.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path


FLAGSHIP_DATA = Path(__file__).resolve().parent.parent / "data" / "flagship_exercises.json"
FLAGSHIP_IDS = {"7-1"}

BLOCKED_CALLS = {
    "open", "exec", "eval", "compile", "__import__", "input", "breakpoint",
    "getattr", "setattr", "delattr", "globals", "locals", "vars", "dir",
    "help", "exit", "quit",
}
BLOCKED_NODES = (
    ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.With, ast.AsyncWith,
    ast.Try,
)


def load_flagship_exercises() -> list[dict]:
    try:
        return json.loads(FLAGSHIP_DATA.read_text(encoding="utf-8"))
    except Exception:
        return []


def get_flagship_exercise(exercise_id: str) -> dict | None:
    return next((item for item in load_flagship_exercises() if item.get("id") == exercise_id), None)


def is_flagship_exercise(exercise_id: str) -> bool:
    return exercise_id in FLAGSHIP_IDS


def _policy_error(code: str) -> str | None:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return f"语法错误：第 {exc.lineno or '?'} 行，{exc.msg}"

    for statement in tree.body:
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant) and isinstance(statement.value.value, str):
            continue
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if statement.decorator_list:
                return "安全检查未通过：不允许使用装饰器"
            continue
        if isinstance(statement, (ast.Assign, ast.AnnAssign)):
            value = statement.value
            try:
                ast.literal_eval(value)
            except Exception:
                return "安全检查未通过：模块级变量只能使用常量值"
            continue
        return "安全检查未通过：模块顶层只能定义函数、类或常量"

    for node in ast.walk(tree):
        if isinstance(node, BLOCKED_NODES):
            return f"安全检查未通过：不允许使用 {type(node).__name__}"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in BLOCKED_CALLS:
            return f"安全检查未通过：不允许调用 {node.func.id}"
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            return "安全检查未通过：不允许访问内部属性"
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            return "安全检查未通过：不允许访问内部名称"
    return None


RUNNER = r'''
import copy
import json
import sys
import time

SAFE_BUILTINS = {
    "ValueError": ValueError, "TypeError": TypeError, "NotImplementedError": NotImplementedError,
    "dict": dict, "list": list, "tuple": tuple, "set": set, "str": str,
    "int": int, "float": float, "bool": bool, "len": len, "range": range,
    "enumerate": enumerate, "zip": zip, "sorted": sorted, "min": min,
    "max": max, "sum": sum, "all": all, "any": any, "isinstance": isinstance,
    "abs": abs, "round": round,
}

with open(sys.argv[1], "r", encoding="utf-8") as source_file:
    source = source_file.read()
namespace = {"__builtins__": SAFE_BUILTINS}
exec(compile(source, "submission.py", "exec"), namespace)
dispatch = namespace.get("dispatch_ticket")
if not callable(dispatch):
    raise ValueError("必须定义 dispatch_ticket(ticket, agents, now_minutes)")

def ticket(**updates):
    value = {"id": "T-100", "category": "billing", "priority": "normal", "vip": False, "created_at": 100}
    value.update(updates)
    return value

def agent(agent_id, skills=("billing",), online=True, active=0, capacity=5):
    return {"id": agent_id, "skills": list(skills), "online": online, "active_cases": active, "capacity": capacity}

cases = []

def case(name, check):
    started = time.perf_counter()
    try:
        check()
        cases.append({"description": name, "passed": True, "error": None, "duration_ms": round((time.perf_counter() - started) * 1000, 2)})
    except Exception as exc:
        cases.append({"description": name, "passed": False, "error": str(exc)[:240], "duration_ms": round((time.perf_counter() - started) * 1000, 2)})

def expect_equal(actual, expected):
    if actual != expected:
        raise AssertionError("返回结果不符合该业务场景")

case("基础分派与返回契约", lambda: expect_equal(
    dispatch(ticket(), [agent("A-01")], 100),
    {"ticket_id": "T-100", "status": "assigned", "agent_id": "A-01", "effective_priority": "normal", "sla_minutes": 120, "reason": "matched_skill_and_capacity"}
))

def excludes_unavailable():
    result = dispatch(ticket(), [agent("A-off", online=False), agent("A-full", active=5, capacity=5), agent("A-skill", skills=("refund",)), agent("A-ok", active=4)], 100)
    if result.get("agent_id") != "A-ok":
        raise AssertionError("未正确排除离线、满载或技能不匹配的客服")
case("候选客服资格过滤", excludes_unavailable)

def load_ratio_not_count():
    result = dispatch(ticket(), [agent("A-low-count", active=1, capacity=2), agent("B-low-ratio", active=2, capacity=10)], 100)
    if result.get("agent_id") != "B-low-ratio":
        raise AssertionError("应比较负载率，而不是当前工单数")
case("按负载率而非绝对工单数选择", load_ratio_not_count)

def vip_escalation():
    result = dispatch(ticket(vip=True), [agent("A")], 100)
    if (result.get("effective_priority"), result.get("sla_minutes")) != ("high", 30):
        raise AssertionError("VIP 优先级升级或 SLA 错误")
case("VIP 优先级升级", vip_escalation)

def waiting_escalation():
    result = dispatch(ticket(priority="low", created_at=0), [agent("A")], 60)
    if (result.get("effective_priority"), result.get("sla_minutes")) != ("normal", 120):
        raise AssertionError("等待时长升级边界错误")
case("等待满 60 分钟升级", waiting_escalation)

def capped_escalation():
    result = dispatch(ticket(priority="high", vip=True, created_at=0), [agent("A")], 600)
    if (result.get("effective_priority"), result.get("sla_minutes")) != ("urgent", 15):
        raise AssertionError("多次升级必须封顶 urgent")
case("优先级升级封顶", capped_escalation)

def deterministic_tie():
    result = dispatch(ticket(), [agent("B-02", active=1), agent("A-01", active=1)], 100)
    if result.get("agent_id") != "A-01":
        raise AssertionError("负载率相同时必须按 id 稳定选择")
case("相同负载率的确定性选择", deterministic_tie)

case("无候选人进入队列", lambda: expect_equal(
    dispatch(ticket(), [agent("A", online=False)], 100),
    {"ticket_id": "T-100", "status": "queued", "agent_id": None, "effective_priority": "normal", "sla_minutes": 120, "reason": "no_eligible_agent"}
))

def input_immutable():
    source_ticket = ticket(vip=True)
    source_agents = [agent("A", active=1)]
    before_ticket, before_agents = copy.deepcopy(source_ticket), copy.deepcopy(source_agents)
    dispatch(source_ticket, source_agents, 100)
    if source_ticket != before_ticket or source_agents != before_agents:
        raise AssertionError("函数不得修改 ticket 或 agents 输入")
case("输入对象保持不变", input_immutable)

def invalid_input():
    invalid_values = [
        ({"category": "billing", "priority": "normal", "vip": False, "created_at": 0}, [agent("A")], 1),
        (ticket(priority="critical"), [agent("A")], 100),
        (ticket(), [agent("A", capacity=0)], 100),
        (ticket(created_at=101), [agent("A")], 100),
    ]
    for args in invalid_values:
        try:
            dispatch(*args)
        except ValueError:
            continue
        raise AssertionError("非法结构或数值必须抛出 ValueError")
case("非法输入统一拒绝", invalid_input)

print("__JUDGE_RESULT__" + json.dumps(cases, ensure_ascii=False))
'''


def judge_submission(exercise_id: str, code: str, timeout: int = 5) -> dict:
    started = time.perf_counter()
    if not is_flagship_exercise(exercise_id):
        raise ValueError(f"{exercise_id} 不是私有场景判题任务")

    policy_error = _policy_error(code)
    if policy_error:
        return {
            "passed": False, "total": 10, "passed_count": 0,
            "compile_error": policy_error, "results": [],
            "execution_time": round(time.perf_counter() - started, 3),
            "judge_mode": "server_private_cases",
        }

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            solution_path = Path(temp_dir) / "submission.py"
            runner_path = Path(temp_dir) / "runner.py"
            solution_path.write_text(code, encoding="utf-8")
            runner_path.write_text(RUNNER, encoding="utf-8")
            proc = subprocess.run(
                [os.environ.get("PYTHON_PATH", "python"), "-I", "-X", "utf8", str(runner_path), str(solution_path)],
                cwd=temp_dir, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
            )
        marker_lines = [line for line in (proc.stdout or "").splitlines() if line.startswith("__JUDGE_RESULT__")]
        if proc.returncode != 0 or not marker_lines:
            error = (proc.stderr or proc.stdout or "提交代码未能完成执行").strip().splitlines()[-1][:300]
            return {
                "passed": False, "total": 10, "passed_count": 0,
                "compile_error": error, "results": [],
                "execution_time": round(time.perf_counter() - started, 3),
                "judge_mode": "server_private_cases",
            }
        raw_results = json.loads(marker_lines[-1].removeprefix("__JUDGE_RESULT__"))
        results = [
            {"case_index": index, **item}
            for index, item in enumerate(raw_results, 1)
        ]
        passed_count = sum(1 for item in results if item["passed"])
        return {
            "passed": passed_count == len(results), "total": len(results), "passed_count": passed_count,
            "compile_error": None, "results": results,
            "execution_time": round(time.perf_counter() - started, 3),
            "judge_mode": "server_private_cases",
        }
    except subprocess.TimeoutExpired:
        return {
            "passed": False, "total": 10, "passed_count": 0,
            "compile_error": f"执行超时（>{timeout} 秒）", "results": [],
            "execution_time": round(time.perf_counter() - started, 3),
            "judge_mode": "server_private_cases",
        }
    except Exception as exc:
        return {
            "passed": False, "total": 10, "passed_count": 0,
            "compile_error": f"判题执行失败：{str(exc)[:240]}", "results": [],
            "execution_time": round(time.perf_counter() - started, 3),
            "judge_mode": "server_private_cases",
        }
