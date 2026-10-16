"""真实文件/进程与拒绝路径；不调用在线模型。"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
from runtime import QUESTION, build_tools, execute_tool, read_file, run_loop, tool_definitions
from practice import scripted_model


def call(name="read_file", arguments=None, call_id="call_read"):
    return {"type": "tool_use", "id": call_id, "name": name,
            "input": {"path": "main.py"} if arguments is None else arguments}


class ToolsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace"
        self.root.mkdir()
        (self.root / "main.py").write_text("print(6 * 7)\n")
        self.tools = build_tools(self.root)

    def test_round_trip_and_budget(self):
        outcome = run_loop(scripted_model, lambda c: execute_tool(c, self.tools),
                           emit=lambda _: None, question=QUESTION)
        self.assertEqual((outcome["status"], outcome["calls"], len(outcome["messages"])), ("answered", 3, 6))
        self.assertEqual(outcome["messages"][0]["content"], QUESTION)
        self.assertEqual(outcome["messages"][2]["content"][0]["tool_use_id"], "call_1")
        self.assertEqual(outcome["messages"][4]["content"][0]["tool_use_id"], "call_2")
        self.assertIn("exit_code=0\n42", outcome["text"])
        limited = run_loop(scripted_model, lambda c: execute_tool(c, self.tools), 1,
                           emit=lambda _: None, question=QUESTION)
        self.assertEqual(limited["status"], "call_limit")
        self.assertEqual(len(limited["messages"]), 3)

    def test_rejection_never_calls_handler(self):
        handler = Mock(return_value="unexpected")
        self.tools["read_file"]["run"] = handler
        for c in [call("delete_file"), call(arguments={}), call(arguments={"path": 4}),
                  call(arguments={"path": "main.py", "extra": True}), call(name=["read_file"])]:
            result = execute_tool(c, self.tools)
            self.assertTrue(result["is_error"])
            self.assertEqual(result["tool_use_id"], "call_read")
        handler.assert_not_called()

    def test_read_boundaries(self):
        outside = self.root.parent / "secret.txt"
        outside.write_text("outside")
        (self.root / "alias").symlink_to(outside)
        for path in ["../secret.txt", str(outside), "alias"]:
            result = execute_tool(call(arguments={"path": path}), self.tools)
            self.assertTrue(result["is_error"])
            self.assertIn("越出", result["content"])
        (self.root / "large").write_bytes(b"x" * 4097)
        self.assertIn("4096", execute_tool(call(arguments={"path": "large"}), self.tools)["content"])
        (self.root / "binary").write_bytes(b"\xff")
        self.assertTrue(execute_tool(call(arguments={"path": "binary"}), self.tools)["is_error"])
        self.assertTrue(execute_tool(call(arguments={"path": "missing"}), self.tools)["is_error"])
        self.assertEqual(read_file(self.root, "main.py"), "print(6 * 7)\n")

    def test_schema_and_registry_share_names(self):
        definitions = tool_definitions(self.tools)
        self.assertEqual([d["name"] for d in definitions], list(self.tools))
        self.assertEqual(definitions[0]["input_schema"]["required"], ["path"])
        self.assertEqual(definitions[1]["input_schema"]["properties"], {})

    def test_multiple_calls_keep_ids_and_order(self):
        def ask(messages):
            if len(messages) == 1:
                return {"stop_reason": "tool_use", "content": [call(call_id="a"), call("run_main", {}, "b")]}
            self.assertEqual([r["tool_use_id"] for r in messages[-1]["content"]], ["a", "b"])
            return {"stop_reason": "end_turn", "content": [{"type": "text", "text": "done"}]}
        self.assertEqual(run_loop(ask, lambda c: execute_tool(c, self.tools), emit=lambda _: None)["status"], "answered")

    def test_real_failure_is_feedback(self):
        (self.root / "main.py").write_text("print(10 / 0)\n")
        result = execute_tool(call("run_main", {}), self.tools)
        self.assertTrue(result["is_error"])
        self.assertIn("ZeroDivisionError", result["content"])
        self.assertEqual(result["tool_use_id"], "call_read")


if __name__ == "__main__":
    unittest.main()
