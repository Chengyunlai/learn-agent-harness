import contextlib
import inspect
import io
from figure_fixtures import FUNCTIONS, CASES, fixture_context

for function in FUNCTIONS:
    for scenario in CASES[function.__name__]:
        context = fixture_context(function.__name__, scenario)
        namespace = {}
        with contextlib.redirect_stdout(io.StringIO()):
            exec(context["setup"], namespace)
            exec(inspect.getsource(function), namespace)
            exec(context["entry"], namespace)
        result = namespace["outcome"]
        if function.__name__ == "execute_guarded":
            assert result["is_error"] == (scenario in ("refused", "blocked"))
            assert namespace["_executions"] == ([] if scenario in ("refused", "blocked") else ["read_file" if scenario == "read" else "run_main"])
            assert result["tool_use_id"] == ("read_1" if scenario == "read" else "run_1")
        elif function.__name__ == "authorize_call":
            assert result["decision"] == ("allow" if scenario == "approved" else "deny")
        else:
            assert result["decision"] == {"read": "allow", "ask": "ask", "blocked": "deny", "invalid": "deny"}[scenario]
        assert len(namespace["_approvals"]) == (function.__name__ != "permission_for" and scenario not in ("blocked", "read"))
        print(function.__name__, scenario, "PASS")
