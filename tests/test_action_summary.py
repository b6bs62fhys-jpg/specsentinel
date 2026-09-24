"""Fahrplan 9: the GitHub Action writes a job summary and annotations.

The summary script (action/summary.py) reads the text report of a real run
and the exit code. It must never change the exit code, must escape everything
that comes from the spec or the API, and must work with the text format of
older pinned versions.
"""
import importlib.util
from pathlib import Path

import yaml

from specsentinel.cli import main

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("action_summary", ROOT / "action" / "summary.py")
assert _spec and _spec.loader
summary = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(summary)


def real_report(capsys, spec_path, url, *extra):
    code = main([spec_path, "--url", url, *extra])
    return code, capsys.readouterr().out


def test_drift_run_gives_error_annotation_per_drifting_operation(capsys, spec_path, start_server):
    code, text = real_report(capsys, spec_path, start_server(drift=True))
    assert code == 1
    annotations = summary.annotation_lines(text, code)
    assert annotations, "drift must produce annotations"
    assert all(a.startswith("::error title=SpecSentinel drift::") for a in annotations)
    drifting = [line for line in text.splitlines() if line.rstrip().endswith("DRIFT") and not line.startswith("Result")]
    assert len(annotations) == len(drifting)


def test_drift_run_summary_names_result_counts_and_operations(capsys, spec_path, start_server):
    code, text = real_report(capsys, spec_path, start_server(drift=True))
    md = summary.markdown(text, code)
    assert md.startswith("## SpecSentinel")
    assert "Drift found (exit code 1)" in md
    assert "checked" in md and "with drift" in md
    assert "| DRIFT |" in md
    assert "<details>" in md and text.strip().splitlines()[0] in md


def test_matching_run_has_no_annotations(capsys, spec_path, start_server):
    code, text = real_report(capsys, spec_path, start_server(drift=False))
    assert code == 0
    assert summary.annotation_lines(text, code) == []
    assert "No drift (exit code 0)" in summary.markdown(text, code)


def test_run_that_could_not_complete(capsys, spec_path):
    code = main([spec_path, "--url", "http://127.0.0.1:1"])
    text = capsys.readouterr()
    assert code == 2
    annotations = summary.annotation_lines(text.out, code)
    assert annotations == ["::error title=SpecSentinel::The check could not be completed (exit code 2)."]
    assert "Check could not be completed (exit code 2)" in summary.markdown(text.out, code)


def test_values_from_spec_or_api_are_escaped():
    text = "GET /x%0A::warning::boom,a:b  200  DRIFT\n"
    [annotation] = summary.annotation_lines(text, 1)
    assert "\n" not in annotation
    assert "%250A" in annotation  # % is escaped first, so no injected newline
    assert annotation.count("::") == 2  # only the command's own separators
    md = summary.markdown("GET /a|b  200  DRIFT\n```\n", 1)
    assert "/a\\|b" in md  # table cell cannot be broken
    assert "````" in md  # fence longer than any backtick run in the report


def test_old_text_format_is_understood():
    old = (
        "SpecSentinel 0.1.1\nSpec:   petstore.yaml\nTarget: http://x\n\n"
        "GET /pets        200  OK\nGET /pets/{id}   200  DRIFT\n"
        "    error   TYPE_MISMATCH   body.id\n\n"
        "2 checked, 1 with drift, 0 skipped, 0 failed\nResult: DRIFT (exit code 1)\n"
    )
    assert summary.annotation_lines(old, 1) == ["::error title=SpecSentinel drift::GET /pets/{id} returned 200 and does not match the spec."]


def test_main_writes_summary_and_never_changes_the_exit_code(tmp_path, capsys):
    report = tmp_path / "report.txt"
    report.write_text("GET /a  200  DRIFT\nResult: DRIFT (exit code 1)\n", encoding="utf-8")
    target = tmp_path / "summary.md"
    assert summary.main([str(report), "1"], {"GITHUB_STEP_SUMMARY": str(target)}) == 0
    assert "Drift found" in target.read_text(encoding="utf-8")
    assert "::error" in capsys.readouterr().out
    # Missing report file or summary target: still exit 0, the action keeps its own code.
    assert summary.main([str(tmp_path / "missing.txt"), "2"], {}) == 0


def test_action_passes_exit_code_through_and_calls_summary():
    action = yaml.safe_load((ROOT / "action.yml").read_text(encoding="utf-8"))
    assert action["inputs"]["summary"]["default"] == "true"
    run = next(s["run"] for s in action["runs"]["steps"] if s.get("name") == "Check API against spec")
    assert "PIPESTATUS[0]" in run
    assert "action/summary.py" in run
    assert run.rstrip().endswith('exit "$code"')
    assert "stop-commands" in run  # report lines cannot trigger workflow commands
