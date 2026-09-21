import json

from specsentinel.cli import main


def run(capsys, *args):
    code = main(list(args))
    return code, json.loads(capsys.readouterr().out)


def test_json_output_for_matching_api(capsys, spec_path, start_server):
    url = start_server(drift=False)
    code, data = run(capsys, spec_path, "--url", url, "--param", "ownerId=1",
                     "--format", "json")
    assert code == 0
    assert data["exit_code"] == 0
    assert data["summary"]["counts"] == {"error": 0, "warning": 0}
    assert data["findings"] == []


def test_json_output_for_drifting_api(capsys, spec_path, start_server):
    url = start_server(drift=True)
    code, data = run(capsys, spec_path, "--url", url, "--format", "json")
    assert code == 1
    assert data["exit_code"] == 1
    assert data["summary"]["counts"]["error"] >= 3

    keys = {"code", "method", "path", "severity"}
    assert data["findings"]
    assert all(set(f) == keys for f in data["findings"])
    assert all(f["method"] == "GET" for f in data["findings"])
    assert all(f["severity"] in ("error", "warning") for f in data["findings"])
    assert {f["code"] for f in data["findings"]}.issuperset(
        {"MISSING_FIELD", "TYPE_MISMATCH", "UNDOCUMENTED_STATUS"})


def test_json_output_when_the_check_fails(capsys, spec_path):
    code, data = run(capsys, spec_path, "--url", "http://127.0.0.1:1",
                     "--timeout", "2", "--format", "json")
    assert code == 2
    assert data["exit_code"] == 2
    assert data["summary"]["failed"] > 0
    assert data["summary"]["counts"] == {"error": 0, "warning": 0}
    assert data["findings"] == []