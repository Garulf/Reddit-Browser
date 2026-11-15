import json
import subprocess
import sys
from pathlib import Path

RUN_PY = Path(__file__).resolve().parents[1] / "src" / "run.py"


def test_plugin_answers_json_rpc_query(tmp_path):
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": [{}]},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "query",
            "params": [{"search": "/", "actionKeyword": "r", "rawQuery": "r /"}, {"favorites": ["Python"]}],
        },
        {"jsonrpc": "2.0", "id": 3, "method": "close", "params": []},
    ]
    stdin = "".join(json.dumps(request) + "\n" for request in requests)
    process = subprocess.run(
        [sys.executable, str(RUN_PY)], input=stdin, capture_output=True, text=True, cwd=tmp_path, timeout=30,
        encoding="utf-8",
    )
    assert process.returncode == 0, process.stderr
    replies = {reply["id"]: reply for reply in map(json.loads, process.stdout.splitlines())}
    (result,) = replies[2]["result"]["result"]
    assert result["Title"] == "r/Python"
    assert result["JsonRPCAction"]["Parameters"] == ["r /Python"]
