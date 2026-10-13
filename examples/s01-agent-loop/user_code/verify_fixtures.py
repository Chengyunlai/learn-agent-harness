"""Execute unchanged formal functions with browser fixtures; no network or file processes."""
import ast
from pathlib import Path
from figure_fixtures import fixture_context

source = (Path(__file__).resolve().parents[1] / "core/runtime.py").read_text()
functions = {node.name: ast.get_source_segment(source, node) for node in ast.parse(source).body
             if isinstance(node, ast.FunctionDef)}
for name, scenarios in {"ask_claude": ["request"], "run_main": ["error", "success", "timeout", "rejected"],
                        "run_loop": ["report", "limit", "truncated"]}.items():
    for scenario in scenarios:
        context = fixture_context(name, scenario)
        ns = {"__name__": "fixture_test"}
        exec(context["setup"], ns)
        # The loop's adapters use the very same formal source as the standalone function figures.
        for code in functions.values():
            exec(code, ns)
        exec(context["entry"], ns)
        outcome = ns["outcome"]
        if name == "ask_claude":
            assert outcome["stop_reason"] == "tool_use" and len(ns["_fixture_requests"]) == 1
            assert not ns["_fixture_executions"]
        elif name == "run_main":
            assert outcome["tool_use_id"] == "call_1"
            assert outcome["is_error"] is (scenario != "success")
            assert len(ns["_fixture_executions"]) == (0 if scenario == "rejected" else 1)
        else:
            expected = {"report": ("answered", 2, 4, 1), "limit": ("call_limit", 1, 3, 1),
                        "truncated": ("model_stopped", 1, 2, 0)}[scenario]
            assert (outcome["status"], outcome["calls"], len(outcome["messages"]), len(ns["_fixture_executions"])) == expected
            assert len(ns["_fixture_requests"]) == expected[1]
print("PASS eight inputs; all three formal function bodies execute unchanged; API/process are explicit teaching substitutes")
