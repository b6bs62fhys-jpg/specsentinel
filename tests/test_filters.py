"""--include and --exclude select which operations are checked."""
import json

from specsentinel.cli import main
from specsentinel.runner import run_check
from specsentinel.spec import load_spec


def result_for(report, path):
    return next(r for r in report.results if r.path == path)


def test_exclude_marks_the_operation_as_skipped(spec_path, start_server):
    url = start_server(drift=False)
    report = run_check(load_spec(spec_path), url, exclude=["/health"])
    assert result_for(report, "/health").skipped == "excluded"
    assert result_for(report, "/pets").skipped is None


def test_include_checks_only_matching_paths(spec_path, start_server):
    url = start_server(drift=False)
    report = run_check(load_spec(spec_path), url, include=["/health"])
    assert [r.path for r in report.checked] == ["/health"]
    assert result_for(report, "/pets").skipped == "excluded"
    assert result_for(report, "/stats").skipped == "excluded"


def test_include_accepts_a_wildcard(spec_path, start_server):
    url = start_server(drift=False)
    report = run_check(load_spec(spec_path), url, include=["/pets*"])
    assert {r.path for r in report.checked} == {"/pets", "/pets/{petId}"}
    assert result_for(report, "/health").skipped == "excluded"


def test_exclude_accepts_a_wildcard(spec_path, start_server):
    url = start_server(drift=False)
    report = run_check(load_spec(spec_path), url, exclude=["/pets*"])
    assert {r.path for r in report.checked} == {"/health", "/stats"}
    assert result_for(report, "/pets").skipped == "excluded"
    assert result_for(report, "/pets/{petId}").skipped == "excluded"


def test_exclude_wins_over_include(spec_path, start_server):
    url = start_server(drift=False)
    report = run_check(load_spec(spec_path), url,
                       include=["/pets*"], exclude=["/pets/{petId}"])
    assert [r.path for r in report.checked] == ["/pets"]
    assert result_for(report, "/pets/{petId}").skipped == "excluded"


def test_excluded_operations_do_not_change_the_exit_code(spec_path, start_server):
    url = start_server(drift=True)  # /pets/{petId} and /stats drift here
    report = run_check(load_spec(spec_path), url,
                       exclude=["/pets/{petId}", "/stats"])
    assert report.exit_code() == 0
    assert result_for(report, "/pets/{petId}").skipped == "excluded"
    assert result_for(report, "/stats").skipped == "excluded"


def test_without_filters_everything_is_checked(spec_path, start_server):
    url = start_server(drift=False)
    report = run_check(load_spec(spec_path), url)
    assert {r.path for r in report.checked} == {"/health", "/pets", "/pets/{petId}", "/stats"}
    assert result_for(report, "/owners/{ownerId}").skipped != "excluded"


def test_excluded_operations_appear_in_json_output(capsys, spec_path, start_server):
    url = start_server(drift=False)
    code = main([spec_path, "--url", url, "--exclude", "/health", "--format", "json"])
    out = capsys.readouterr()
    assert code == 0
    data = json.loads(out.out)
    health = next(op for op in data["operations"] if op["path"] == "/health")
    assert health["state"] == "SKIPPED"
    assert health["skipped"] == "excluded"
    assert data["summary"]["skipped"] == 2  # /health and /owners/{ownerId}
