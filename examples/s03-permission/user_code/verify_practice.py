"""验证宿主决策、调用快照和真实程序是否曾启动。"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
from runtime import QUESTION, authorize_call, build_tools, execute_guarded, permission_for, run_loop
from practice import scripted_model


def call(name="run_main", arguments=None):
    return {"id": "run_1", "type": "tool_use", "name": name,
            "input": {} if arguments is None else arguments}


class PermissionChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "main.py").write_text("from pathlib import Path\nPath('ran').touch()\nprint(42)\n")
        self.tools = build_tools(self.root)

    def test_denied_and_blocked_never_start_program(self):
        for blocked, answer in [((), False), (("run_main",), True)]:
            approve = Mock(return_value=answer)
            result = execute_guarded(call(), self.tools, approve, blocked)
            self.assertTrue(result["is_error"])
            self.assertEqual(result["tool_use_id"], "run_1")
            self.assertFalse((self.root / "ran").exists())
            self.assertEqual(approve.call_count, 0 if blocked else 1)
            self.assertIn("未执行", result["content"])

    def test_allowed_starts_real_program(self):
        result = execute_guarded(call(), self.tools, lambda *_: True)
        self.assertFalse(result["is_error"])
        self.assertTrue((self.root / "ran").exists())
        self.assertIn("exit_code=0\n42", result["content"])

    def test_read_does_not_ask(self):
        approve = Mock(side_effect=AssertionError("read must not ask"))
        result = execute_guarded(call("read_file", {"path": "main.py"}), self.tools, approve)
        self.assertFalse(result["is_error"])
        self.assertFalse((self.root / "ran").exists())

    def test_invalid_calls_never_ask_or_execute(self):
        approve = Mock(side_effect=AssertionError("invalid call must not ask"))
        for request in [call("unknown"), call(arguments={"approved": True}), call("read_file", {"path": 42})]:
            self.assertTrue(execute_guarded(request, self.tools, approve)["is_error"])
        self.assertFalse((self.root / "ran").exists())
        self.tools["new_tool"] = {"parameters": {}, "run": Mock()}
        self.assertEqual(permission_for(call("new_tool"), self.tools)["decision"], "deny")

    def test_only_boolean_true_grants(self):
        for value in ["allow", "yes", 1, None, False]:
            self.assertEqual(authorize_call(call(), self.tools, lambda *_: value)["decision"], "deny")
        self.assertFalse((self.root / "ran").exists())

    def test_prompt_cannot_mutate_executed_snapshot(self):
        original = call("run_main")
        def approve(shown, _):
            shown["name"] = "read_file"; shown["input"] = {"path": "missing"}
            original["name"] = "unknown"; original["id"] = "changed"
            return True
        result = execute_guarded(original, self.tools, approve)
        self.assertFalse(result["is_error"])
        self.assertEqual(result["tool_use_id"], "run_1")
        self.assertTrue((self.root / "ran").exists())

    def test_denial_reaches_model_with_id_and_goal(self):
        observed = []
        def ask(messages):
            if len(messages) == 5:
                observed.append(messages[-1]["content"][0].copy())
                self.assertEqual(messages[0]["content"], QUESTION)
            return scripted_model(messages)
        outcome = run_loop(ask, lambda c: execute_guarded(c, self.tools, lambda *_: False),
                           emit=lambda _: None, question=QUESTION)
        self.assertEqual(outcome["status"], "answered")
        self.assertEqual((observed[0]["tool_use_id"], observed[0]["is_error"]), ("run_1", True))
        self.assertFalse((self.root / "ran").exists())
        self.assertEqual(len(outcome["messages"]), 6)

    def test_host_exception_cannot_execute(self):
        with self.assertRaises(RuntimeError):
            execute_guarded(call(), self.tools, Mock(side_effect=RuntimeError("host failed")))
        self.assertFalse((self.root / "ran").exists())

    def test_budget_still_bounds_repeated_denial(self):
        denied = lambda _: {"stop_reason": "tool_use", "content": [call()]}
        outcome = run_loop(denied, lambda c: execute_guarded(c, self.tools, lambda *_: False),
                           max_calls=2, emit=lambda _: None, question=QUESTION)
        self.assertEqual(outcome["status"], "call_limit")
        self.assertFalse((self.root / "ran").exists())


if __name__ == "__main__":
    unittest.main()
