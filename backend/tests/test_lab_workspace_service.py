import tempfile
import unittest
import os
from pathlib import Path
from unittest.mock import patch

from services import lab_workspace_service as service


CORRECT_BUILD_CHAT_MESSAGES = '''
def build_chat_messages(system_prompt, user_input):
    if not isinstance(system_prompt, str) or not system_prompt.strip():
        raise ValueError("system_prompt 不能为空")
    if not isinstance(user_input, str) or not user_input.strip():
        raise ValueError("user_input 不能为空")
    return [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": user_input.strip()},
    ]
'''

CORRECT_NORMALIZE_STREAM_CHUNKS = '''
def normalize_stream_chunks(chunks):
    parts = []
    for chunk in chunks:
        if chunk is None:
            continue
        if isinstance(chunk, str):
            content = chunk
        elif isinstance(chunk, dict):
            content = chunk.get("content")
        elif hasattr(chunk, "content"):
            content = chunk.content
        else:
            raise ValueError("不支持的片段")
        if content is None or content == "":
            continue
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text")
                    if isinstance(text, str) and text:
                        parts.append(text)
        else:
            raise ValueError("不支持的内容")
    return "".join(parts)
'''

CHAT_APP = '''
from langchain_openai import ChatOpenAI
from solution import build_chat_messages

model = ChatOpenAI(model="demo")
messages = build_chat_messages("称呼用户为小林", "推荐一座博物馆")
response = model.invoke(messages)
print(response.content)
'''

STREAM_APP = '''
from langchain_openai import ChatOpenAI
from solution import normalize_stream_chunks

model = ChatOpenAI(model="demo")
messages = [{"role": "user", "content": "你好"}]
parts = []
for chunk in model.stream(messages):
    text = normalize_stream_chunks([chunk])
    print(text, end="", flush=True)
    parts.append(text)
answer = "".join(parts)
'''


class LabWorkspaceServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root_patch = patch.object(service, "WORKSPACE_ROOT", Path(self.temp.name))
        self.root_patch.start()

    def tearDown(self):
        self.root_patch.stop()
        self.temp.cleanup()

    def test_workspace_starts_as_a_real_small_project(self):
        workspace = service.get_workspace(7, "1-1")
        self.assertEqual(workspace["project_name"], "agent-lab-1-1")
        self.assertEqual({item["path"] for item in workspace["files"]}, {"README.md", ".gitignore"})
        self.assertEqual(len(workspace["course"]["stages"]), 6)

    def test_structure_and_dependency_checks_are_incremental(self):
        for name in ["requirements.txt", ".env", "solution.py", "app.py"]:
            service.save_file(7, "1-1", name, "")
        structure = service.check_stage(7, "1-1", "structure")
        self.assertTrue(structure["passed"])

        service.save_file(
            7, "1-1", "requirements.txt",
            "langchain>=1.0\nlangchain-openai>=1.0\npython-dotenv>=1.0\n",
        )
        root = service._root(7, "1-1")
        state = service._read_state(root)
        state["installed_requirements_hash"] = service._requirements_hash(root)
        service._write_state(root, state)
        dependencies = service.check_stage(7, "1-1", "dependencies")
        self.assertTrue(dependencies["passed"])
        self.assertIn("dependencies", dependencies["completed_stages"])

    def test_checker_reports_exact_missing_target(self):
        service.get_workspace(7, "1-1")
        service.save_file(7, "1-1", "solution.py", "def something_else():\n    return 1\n")
        result = service.check_stage(7, "1-1", "implementation")
        self.assertFalse(result["passed"])
        target = next(item for item in result["checks"] if item["label"] == "build_chat_messages")
        self.assertIn("还没有定义", target["detail"])

    def test_implementation_stage_rejects_a_function_with_no_behavior(self):
        service.get_workspace(7, "1-1")
        for body in ("pass", "raise NotImplementedError"):
            with self.subTest(body=body):
                service.save_file(
                    7, "1-1", "solution.py",
                    f"def build_chat_messages(system_prompt, user_input):\n    {body}\n",
                )

                result = service.check_stage(7, "1-1", "implementation")

                self.assertFalse(result["passed"])
                behavior = next(item for item in result["checks"] if item["label"] == "核心函数行为")
                self.assertFalse(behavior["passed"])
                self.assertIn("基础消息顺序", behavior["detail"])
                self.assertNotIn("implementation", result["completed_stages"])

    def test_implementation_stage_requires_all_business_scenarios(self):
        service.get_workspace(7, "1-1")
        service.save_file(7, "1-1", "solution.py", CORRECT_BUILD_CHAT_MESSAGES)

        result = service.check_stage(7, "1-1", "implementation")

        self.assertTrue(result["passed"], result)
        behavior = next(item for item in result["checks"] if item["label"] == "核心函数行为")
        self.assertEqual(behavior["detail"], "通过 9/9 个业务场景，函数已有可运行的真实行为")
        self.assertEqual(len(behavior["cases"]), 9)
        self.assertIn("implementation", result["completed_stages"])

    def test_integration_stage_rechecks_solution_instead_of_trusting_a_definition(self):
        service.get_workspace(7, "1-1")
        service.save_file(
            7, "1-1", "solution.py",
            "def build_chat_messages(system_prompt, user_input):\n    raise NotImplementedError\n",
        )
        service.save_file(7, "1-1", "app.py", CHAT_APP)

        result = service.check_stage(7, "1-1", "integration")

        self.assertFalse(result["passed"])
        behavior = next(item for item in result["checks"] if item["label"] == "核心模块业务测试")
        self.assertFalse(behavior["passed"])
        self.assertEqual(len(behavior["cases"]), 9)

    def test_chat_integration_requires_personalized_messages_to_reach_invoke(self):
        service.get_workspace(7, "1-1")
        service.save_file(7, "1-1", "solution.py", CORRECT_BUILD_CHAT_MESSAGES)
        service.save_file(7, "1-1", "app.py", CHAT_APP)

        result = service.check_stage(7, "1-1", "integration")

        self.assertTrue(result["passed"], result)
        wiring = next(item for item in result["checks"] if item["label"] == "个性化消息接入")
        self.assertTrue(wiring["passed"])

    def test_stream_integration_requires_incremental_flush_inside_stream_loop(self):
        service.get_workspace(7, "1-3")
        service.save_file(7, "1-3", "solution.py", CORRECT_NORMALIZE_STREAM_CHUNKS)
        service.save_file(7, "1-3", "app.py", STREAM_APP)

        result = service.check_stage(7, "1-3", "integration")

        self.assertTrue(result["passed"], result)
        immediate = next(item for item in result["checks"] if item["label"] == "逐片段即时输出")
        self.assertTrue(immediate["passed"])

    def test_stream_integration_rejects_printing_only_after_collection(self):
        service.get_workspace(7, "1-3")
        service.save_file(7, "1-3", "solution.py", CORRECT_NORMALIZE_STREAM_CHUNKS)
        service.save_file(
            7, "1-3", "app.py",
            STREAM_APP.replace('print(text, end="", flush=True)\n    ', ''),
        )

        result = service.check_stage(7, "1-3", "integration")

        self.assertFalse(result["passed"])
        immediate = next(item for item in result["checks"] if item["label"] == "逐片段即时输出")
        self.assertFalse(immediate["passed"])

    def test_terminal_supports_normal_shell_features(self):
        service.get_workspace(7, "1-1")
        result = service.run_terminal(7, "1-1", "echo first && echo second")
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("first", result["output"])
        self.assertIn("second", result["output"])

    def test_terminal_keeps_one_canonical_venv_and_project_directories(self):
        service.get_workspace(7, "1-1")
        created = service.create_directory(7, "1-1", "src/tools")
        self.assertEqual(created["path"], "src/tools")
        mkdir_command = "mkdir data\\cache" if os.name == "nt" else "mkdir -p data/cache"
        terminal_folder = service.run_terminal(7, "1-1", mkdir_command)
        self.assertEqual(terminal_folder["exit_code"], 0)
        workspace = service.get_workspace(7, "1-1")
        self.assertIn("src/tools", workspace["directories"])
        self.assertIn("data/cache", workspace["directories"])

        custom_env = service.run_terminal(7, "1-1", "python -m venv 123")
        self.assertEqual(custom_env["exit_code"], 0)
        self.assertIn("统一为 .venv", custom_env["output"])
        self.assertEqual(service.get_workspace(7, "1-1")["virtual_envs"], [".venv"])

    def test_terminal_can_create_and_read_project_files(self):
        service.get_workspace(7, "1-1")
        result = service.run_terminal(7, "1-1", "echo terminal-created > notes.txt")
        self.assertEqual(result["exit_code"], 0)
        file = service.read_file(7, "1-1", "notes.txt")
        self.assertFalse(file["binary"])
        self.assertIn("terminal-created", file["content"])

    def test_virtual_environment_is_browsable_and_activation_persists(self):
        service.get_workspace(7, "1-1")
        created = service.run_terminal(7, "1-1", "python -m venv venv")
        self.assertEqual(created["exit_code"], 0)
        entries = service.list_entries(7, "1-1")["entries"]
        self.assertTrue(any(item["name"] == ".venv" and item["virtual"] for item in entries))
        self.assertTrue(any(item["name"] == "pyvenv.cfg" for item in service.list_entries(7, "1-1", ".venv")["entries"]))

        activated = service.run_terminal(7, "1-1", "source .venv/bin/activate")
        self.assertEqual(activated["active_env"], ".venv")
        version = service.run_terminal(7, "1-1", "python --version")
        self.assertEqual(version["active_env"], ".venv")
        deactivated = service.run_terminal(7, "1-1", "deactivate")
        self.assertEqual(deactivated["active_env"], "")

    def test_terminal_stream_emits_output_before_done(self):
        service.get_workspace(7, "1-1")
        events = list(service.stream_terminal(7, "1-1", "echo streaming"))
        event_types = [item["type"] for item in events]
        self.assertEqual(event_types[0], "start")
        self.assertIn("output", event_types)
        self.assertEqual(event_types[-1], "done")
        self.assertIn("streaming", "".join(item.get("data", "") for item in events))

    def test_explorer_can_rename_duplicate_and_delete_entries(self):
        service.get_workspace(7, "1-1")
        service.save_file(7, "1-1", "src/tool.py", "print('ok')\n")
        moved = service.move_entry(7, "1-1", "src/tool.py", "src/main.py")
        self.assertTrue(moved["moved"])
        copied = service.duplicate_entry(7, "1-1", "src/main.py", "src/main-copy.py")
        self.assertTrue(copied["duplicated"])
        deleted = service.delete_entry(7, "1-1", "src/main-copy.py")
        self.assertTrue(deleted["deleted"])
        self.assertFalse(service._root(7, "1-1").joinpath("src/main-copy.py").exists())

    def test_progress_overview_uses_the_same_stage_state_as_workspace(self):
        service.get_workspace(7, "1-1")
        root = service._root(7, "1-1")
        service._write_state(root, {"completed_stages": ["structure", "environment"], "commands": []})
        overview = service.get_progress_overview(7)
        self.assertEqual(overview["1-1"]["completed_stages"], ["structure", "environment"])
        self.assertEqual(overview["1-1"]["total_stages"], 6)


if __name__ == "__main__":
    unittest.main()
