"""Baseline files: record accepted findings so only new drift fails."""
import json

from specsentinel.cli import main


def run(capsys, *args):
    code = main(list(args))
    return code, capsys.readouterr()


def write_baseline(path, entries):
    path.write_text(json.dumps({"findings": entries}), encoding="utf-8")


def test_write_baseline_records_all_findings(capsys, tmp_path, spec_path, start_server):
    url = start_server(drift=True)
    baseline = tmp_path / "baseline.json"
    code, out = run(capsys, spec_path, "--url", url, "--write-baseline", str(baseline))
    assert code == 0  # writing the baseline is the goal, so the run succeeds
    assert "Wrote 4 findings" in out.out
    data = json.loads(baseline.read_text())
    codes = {entry["code"] for entry in data["findings"]}
    assert {"MISSING_FIELD", "TYPE_MISMATCH", "UNDOCUMENTED_STATUS"} <= codes
    for entry in data["findings"]:
        assert {"method", "path", "code", "location"} <= set(entry)


def test_baseline_suppresses_known_findings(capsys, tmp_path, spec_path, start_server):
    url = start_server(drift=True)
    baseline = tmp_path / "baseline.json"
    run(capsys, spec_path, "--url", url, "--write-baseline", str(baseline))
    code, out = run(capsys, spec_path, "--url", url, "--baseline", str(baseline))
    assert code == 0
    assert "4 baselined" in out.out
    assert "Result: MATCH" in out.out


def test_new_findings_still_fail(capsys, tmp_path, spec_path, start_server):
    conforming = start_server(drift=False)
    baseline = tmp_path / "baseline.json"
    run(capsys, spec_path, "--url", conforming, "--param", "ownerId=1",
        "--write-baseline", str(baseline))
    drifting = start_server(drift=True)
    code, out = run(capsys, spec_path, "--url", drifting, "--baseline", str(baseline))
    assert code == 1
    assert "MISSING_FIELD" in out.out


def test_baseline_matches_by_key_not_message(capsys, tmp_path, spec_path, start_server):
    url = start_server(drift=True)
    baseline = tmp_path / "baseline.json"
    write_baseline(baseline, [{
        "method": "GET", "path": "/pets/{petId}", "code": "MISSING_FIELD",
        "location": "body.name", "message": "a completely different wording",
    }])
    code, out = run(capsys, spec_path, "--url", url, "--baseline", str(baseline))
    assert code == 1
    assert "MISSING_FIELD" not in out.out  # matched by key, so suppressed
    assert "TYPE_MISMATCH" in out.out      # everything else is still new


def test_fixed_findings_are_reported(capsys, tmp_path, spec_path, start_server):
    url = start_server(drift=False)
    baseline = tmp_path / "baseline.json"
    write_baseline(baseline, [{
        "method": "GET", "path": "/health", "code": "MISSING_FIELD",
        "location": "body.status", "severity": "error",
    }])
    code, out = run(capsys, spec_path, "--url", url, "--param", "ownerId=1",
                    "--baseline", str(baseline))
    assert code == 0
    assert "no longer occur (fixed)" in out.out
    assert "MISSING_FIELD" in out.out


def test_fixed_findings_in_json_output(capsys, tmp_path, spec_path, start_server):
    url = start_server(drift=False)
    baseline = tmp_path / "baseline.json"
    write_baseline(baseline, [{
        "method": "GET", "path": "/health", "code": "MISSING_FIELD",
        "location": "body.status", "severity": "error",
    }])
    code, out = run(capsys, spec_path, "--url", url, "--param", "ownerId=1",
                    "--baseline", str(baseline), "--format", "json")
    data = json.loads(out.out)
    assert code == 0
    assert data["summary"]["baselined"] == 0
    assert data["fixed"] == [{
        "code": "MISSING_FIELD", "method": "GET", "path": "/health",
        "location": "body.status", "severity": "error",
    }]


def test_baseline_counts_in_json_output(capsys, tmp_path, spec_path, start_server):
    url = start_server(drift=True)
    baseline = tmp_path / "baseline.json"
    run(capsys, spec_path, "--url", url, "--write-baseline", str(baseline))
    code, out = run(capsys, spec_path, "--url", url, "--baseline", str(baseline),
                    "--format", "json")
    data = json.loads(out.out)
    assert code == 0
    assert data["summary"]["baselined"] == 4
    assert data["findings"] == []
    assert data["fixed"] == []


def test_baselined_warning_does_not_fail_with_strict(capsys, tmp_path, spec_path, start_server):
    url = start_server(drift=True)
    baseline = tmp_path / "baseline.json"
    run(capsys, spec_path, "--url", url, "--write-baseline", str(baseline))
    code, _ = run(capsys, spec_path, "--url", url, "--strict", "--baseline", str(baseline))
    assert code == 0
    code, _ = run(capsys, spec_path, "--url", url, "--strict")
    assert code == 1  # without the baseline the warning still fails under strict


def test_missing_baseline_file_exits_2(capsys, spec_path):
    code, out = run(capsys, spec_path, "--url", "http://127.0.0.1:1",
                    "--baseline", "nope.json")
    assert code == 2
    assert "Baseline file not found" in out.err


def test_broken_baseline_file_exits_2(capsys, tmp_path, spec_path):
    baseline = tmp_path / "baseline.json"
    baseline.write_text("{not json")
    code, out = run(capsys, spec_path, "--url", "http://127.0.0.1:1",
                    "--baseline", str(baseline))
    assert code == 2
    assert "not valid JSON" in out.err


def test_malformed_baseline_file_exits_2(capsys, tmp_path, spec_path):
    baseline = tmp_path / "baseline.json"
    baseline.write_text('{"findings": [{"method": "GET"}]}')
    code, out = run(capsys, spec_path, "--url", "http://127.0.0.1:1",
                    "--baseline", str(baseline))
    assert code == 2
    assert "method, path, code and location" in out.err


def test_unwritable_baseline_path_exits_2(capsys, tmp_path, spec_path, start_server):
    url = start_server(drift=True)
    target = tmp_path / "missing-dir" / "baseline.json"
    code, out = run(capsys, spec_path, "--url", url, "--write-baseline", str(target))
    assert code == 2
    assert "Could not write baseline file" in out.err
