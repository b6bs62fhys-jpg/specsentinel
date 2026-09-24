"""The scripts in examples/ run as documented in examples/README.md.

Each script starts the demo API on a free port, runs SpecSentinel and ends
with the exit code of its last check.
"""
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="the examples are bash scripts")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def run_example(name: str, tmp_path: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    # The interpreter running the tests has SpecSentinel installed.
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    env["PYTHON"] = sys.executable
    env["PORT"] = str(_free_port())
    env["WORKDIR"] = str(tmp_path)
    return subprocess.run(["bash", str(EXAMPLES / name)], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=120)


def test_there_are_at_least_three_documented_examples():
    scripts = sorted(p.name for p in EXAMPLES.glob("[0-9][0-9]_*.sh"))
    assert len(scripts) >= 3
    readme = (EXAMPLES / "README.md").read_text(encoding="utf-8")
    for name in scripts:
        assert name in readme, f"{name} is not described in examples/README.md"


def test_simple_run_reports_drift(tmp_path):
    result = run_example("01_simple_run.sh", tmp_path)
    assert result.returncode == 1, result.stderr
    assert "GET /pets/{petId}      200  DRIFT" in result.stdout
    assert "Result: DRIFT (exit code 1)" in result.stdout
    assert "Result: MATCH (exit code 0)" in result.stdout  # the conforming run


def test_baseline_flow_accepts_known_drift_only(tmp_path):
    result = run_example("02_baseline.sh", tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "specsentinel-baseline.json").is_file()
    assert "Result: MATCH (exit code 0)" in result.stdout
    assert "baselined" in result.stdout


def test_swagger2_source_is_checked(tmp_path):
    result = run_example("03_swagger2.sh", tmp_path)
    assert result.returncode == 1, result.stderr
    assert "Spec:   examples/swagger2.yaml" in result.stdout
    assert "4 checked, 2 with drift, 0 skipped, 0 failed" in result.stdout


def test_examples_leave_no_server_running(tmp_path):
    port = _free_port()
    env = dict(os.environ, PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", ""),
               PYTHON=sys.executable, PORT=str(port), WORKDIR=str(tmp_path))
    subprocess.run(["bash", str(EXAMPLES / "01_simple_run.sh")], cwd=ROOT, env=env,
                   capture_output=True, text=True, timeout=120)
    with socket.socket() as s:
        assert s.connect_ex(("127.0.0.1", port)) != 0, "demo server still running after the example"
