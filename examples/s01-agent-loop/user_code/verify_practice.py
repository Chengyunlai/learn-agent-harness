"""真实子进程 + 离线响应验证；不需要 SDK，不访问模型服务。"""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
from runtime import QUESTION, run_loop, run_main


def request(call_id="call_1", name="run_main", inputs=None):
    return {"stop_reason": "tool_use", "content": [{
        "type": "tool_use", "id": call_id, "name": name, "input": inputs or {},
    }]}


def answer(text="已读取执行结果"):
    return {"stop_reason": "end_turn", "content": [{"type": "text", "text": text}]}


class LoopChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.execute = lambda call: run_main(call, self.workspace, timeout=0.2)

    def loop(self, responses, **kwargs):
        seen = []
        iterator = iter(responses)

        def ask(messages):
            seen.append(copy.deepcopy(messages))
            return next(iterator)

        return run_loop(ask, self.execute, emit=lambda _: None, **kwargs), seen

    def test_result_reaches_second_request_with_goal_and_call_id(self):
        (self.workspace / "main.py").write_text("print(10 / 0)\n")
        outcome, seen = self.loop([request(), answer()])
        self.assertEqual(outcome["status"], "answered")
        self.assertEqual(len(seen), 2)
        self.assertEqual(seen[1][0]["content"], QUESTION)
        self.assertEqual(seen[1][1]["content"][0]["id"], "call_1")
        result = seen[1][2]["content"][0]
        self.assertEqual(result["tool_use_id"], "call_1")
        self.assertTrue(result["is_error"])
        self.assertIn("exit_code=1", result["content"])
        self.assertIn("ZeroDivisionError", result["content"])
        self.assertEqual(len(outcome["messages"]), 4)

    def test_successful_process_returns_output(self):
        (self.workspace / "main.py").write_text("print(10 / 2)\n")
        outcome, _ = self.loop([request(), answer()])
        result = outcome["messages"][2]["content"][0]
        self.assertFalse(result["is_error"])
        self.assertEqual(result["content"], "exit_code=0\n5.0")

    def test_timeout_returns_error_and_allows_answer(self):
        (self.workspace / "main.py").write_text("import time\ntime.sleep(5)\n")
        outcome, _ = self.loop([request(), answer()])
        result = outcome["messages"][2]["content"][0]
        self.assertTrue(result["is_error"])
        self.assertIn("运行超时", result["content"])
        self.assertEqual(outcome["status"], "answered")

    def test_call_limit_keeps_last_result_without_extra_model_call(self):
        (self.workspace / "main.py").write_text("print('done')\n")
        outcome, seen = self.loop([request("one"), request("two")], max_calls=2)
        self.assertEqual(outcome["status"], "call_limit")
        self.assertEqual(len(seen), 2)
        self.assertEqual(outcome["messages"][-1]["content"][0]["tool_use_id"], "two")
        self.assertIn("done", outcome["messages"][-1]["content"][0]["content"])

    def test_truncation_never_executes_tool(self):
        response = request()
        response["stop_reason"] = "max_tokens"
        outcome = run_loop(lambda _: response, lambda _: self.fail("不应执行"), emit=lambda _: None)
        self.assertEqual(outcome["status"], "model_stopped")

    def test_unknown_tool_and_arguments_cannot_execute_file(self):
        (self.workspace / "main.py").write_text("from pathlib import Path\nPath('ran').touch()\n")
        for response in [request(name="bash"), request(inputs={"command": "echo test"})]:
            outcome, _ = self.loop([response, answer()])
            self.assertTrue(outcome["messages"][2]["content"][0]["is_error"])
        self.assertFalse((self.workspace / "ran").exists())

    def test_empty_answer_and_conflicting_response_stop(self):
        duplicate = request()
        duplicate["content"] *= 2
        for response in [answer(""), {"stop_reason": "tool_use", "content": []}, duplicate]:
            with self.subTest(response=response):
                outcome = run_loop(lambda _: response, lambda _: self.fail("不应执行"), emit=lambda _: None)
                self.assertEqual(outcome["status"], "protocol_error")

    def test_all_calls_get_associated_results_before_next_model_request(self):
        (self.workspace / "main.py").write_text("print('ok')\n")
        multiple = request("one")
        multiple["content"].extend(request("two")["content"])
        outcome, seen = self.loop([multiple, answer()])
        self.assertEqual([block["tool_use_id"] for block in seen[1][-1]["content"]], ["one", "two"])
        self.assertEqual(outcome["status"], "answered")

    def test_api_failure_returns_control_without_running_tool(self):
        def ask(_):
            raise ConnectionError("测试异常，不是在线请求")
        outcome = run_loop(ask, lambda _: self.fail("不应执行"), emit=lambda _: None)
        self.assertEqual(outcome["status"], "model_error")
        self.assertEqual(len(outcome["messages"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
