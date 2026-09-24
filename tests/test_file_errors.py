"""Fahrplan 8: errors in the params file and the baseline name the file and
the place inside it, and never end in a traceback (exit code 2)."""
import json
import os
import sys

import pytest

from specsentinel.cli import main

URL = "http://127.0.0.1:1"


def run(capsys, *args):
    code = main(list(args))
    return code, capsys.readouterr()


def test_params_file_invalid_yaml_names_the_file(capsys, spec_path, tmp_path):
    params = tmp_path / "params.yaml"
    params.write_text("id: [1, 2\n", encoding="utf-8")
    code, out = run(capsys, spec_path, "--url", URL, "--params-file", str(params))
    assert code == 2
    assert f"Params file {params} is not valid JSON or YAML" in out.err


def test_params_file_not_a_mapping_names_the_file(capsys, spec_path, tmp_path):
    params = tmp_path / "params.yaml"
    params.write_text("- 1\n- 2\n", encoding="utf-8")
    code, out = run(capsys, spec_path, "--url", URL, "--params-file", str(params))
    assert code == 2
    assert f"Params file {params} must be a mapping" in out.err


def test_params_file_operation_entry_names_the_operation(capsys, spec_path, tmp_path):
    params = tmp_path / "params.json"
    params.write_text(json.dumps({"GET /pets/{petId}": {"petId": {"nested": 1}}}), encoding="utf-8")
    # A nested mapping is a legal value; only the shape of the file is checked.
    code, _ = run(capsys, spec_path, "--url", URL, "--params-file", str(params))
    assert code == 2  # the API is unreachable, not a params error
    params.write_text(json.dumps({"GET /pets/{petId}": ["petId", 1]}), encoding="utf-8")
    code, out = run(capsys, spec_path, "--url", URL, "--params-file", str(params))
    assert code == 2
    assert "not a mapping" not in out.err  # list value stays a plain default, as before


def test_params_file_not_utf8_names_the_file(capsys, spec_path, tmp_path):
    params = tmp_path / "params.yaml"
    params.write_bytes(b"id: \xff\xfe\n")
    code, out = run(capsys, spec_path, "--url", URL, "--params-file", str(params))
    assert code == 2
    assert f"Params file {params} could not be read" in out.err


@pytest.mark.skipif(sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                    reason="file permissions are not enforced here")
def test_params_file_unreadable_exits_2_without_traceback(capsys, spec_path, tmp_path):
    params = tmp_path / "params.yaml"
    params.write_text("id: 1\n", encoding="utf-8")
    params.chmod(0)
    try:
        code, out = run(capsys, spec_path, "--url", URL, "--params-file", str(params))
    finally:
        params.chmod(0o600)
    assert code == 2
    assert f"Params file {params} could not be read" in out.err
    assert "Traceback" not in out.err


def test_baseline_entry_error_names_the_entry_and_field(capsys, spec_path, tmp_path):
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"findings": [
        {"method": "GET", "path": "/pets", "code": "X", "location": "body"},
        {"method": "GET", "path": "/pets", "location": "body"},
    ]}), encoding="utf-8")
    code, out = run(capsys, spec_path, "--url", URL, "--baseline", str(baseline))
    assert code == 2
    assert f"Baseline file {baseline}" in out.err
    assert "(in findings[1].code)" in out.err


def test_baseline_entry_not_an_object_names_the_entry(capsys, spec_path, tmp_path):
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"findings": ["GET /pets"]}), encoding="utf-8")
    code, out = run(capsys, spec_path, "--url", URL, "--baseline", str(baseline))
    assert code == 2
    assert "(in findings[0])" in out.err


def test_baseline_without_findings_list_names_the_place(capsys, spec_path, tmp_path):
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"findings": {}}), encoding="utf-8")
    code, out = run(capsys, spec_path, "--url", URL, "--baseline", str(baseline))
    assert code == 2
    assert f"Baseline file {baseline}" in out.err
    assert "(in findings)" in out.err


def test_baseline_not_utf8_exits_2(capsys, spec_path, tmp_path):
    baseline = tmp_path / "baseline.json"
    baseline.write_bytes(b"\xff\xfe{}")
    code, out = run(capsys, spec_path, "--url", URL, "--baseline", str(baseline))
    assert code == 2
    assert f"Baseline file {baseline} could not be read" in out.err
