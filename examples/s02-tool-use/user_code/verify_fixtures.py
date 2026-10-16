import contextlib
import inspect
import io
from figure_fixtures import CASES, fixture_context
from runtime import build_tools, execute_tool, read_file

for function in (build_tools, execute_tool, read_file):
    for scenario in CASES[function.__name__]:
        context = fixture_context(function.__name__, scenario)
        namespace = {}
        with contextlib.redirect_stdout(io.StringIO()):
            exec(context["setup"], namespace)
            exec(inspect.getsource(function), namespace)
            exec(context["entry"], namespace)
        outcome = namespace["outcome"]
        if function is execute_tool:
            assert outcome["is_error"] == (scenario in ("unknown", "arguments"))
            assert outcome["tool_use_id"] == "call_1"
            assert len(namespace["_reads"]) == (scenario == "read")
            assert len(namespace["_runs"]) == (scenario == "run")
        if function is read_file:
            assert ("越出" in outcome) == (scenario == "outside")
            assert ("4096" in outcome) == (scenario == "large")
            assert len(namespace["_reads"]) == (scenario != "outside")
        print(function.__name__, scenario, "PASS")
