"""--format junit renders one testcase per operation as valid XML."""
import xml.etree.ElementTree as ET

from specsentinel.cli import main
from specsentinel.report import render_junit
from specsentinel.runner import OperationResult, Report


def run(capsys, *args):
    code = main(list(args))
    return code, capsys.readouterr().out


def op(method, path, **kwargs):
    r = OperationResult(method=method, path=path)
    for key, value in kwargs.items():
        setattr(r, key, value)
    return r


def test_junit_is_valid_xml_with_one_testcase_per_operation(capsys, spec_path, start_server):
    url = start_server(drift=True)
    code, xml = run(capsys, spec_path, "--url", url, "--format", "junit")
    root = ET.fromstring(xml)
    cases = root.findall(".//testcase")
    assert code == 1
    assert root.tag == "testsuites"
    assert len(cases) == 5
    assert {c.get("name") for c in cases} == {
        "GET /health", "GET /pets", "GET /pets/{petId}", "GET /stats",
        "GET /owners/{ownerId}",
    }


def test_junit_failure_contains_code_and_location(capsys, spec_path, start_server):
    url = start_server(drift=True)
    _, xml = run(capsys, spec_path, "--url", url, "--format", "junit")
    root = ET.fromstring(xml)
    case = next(c for c in root.findall(".//testcase")
                if c.get("name") == "GET /pets/{petId}")
    failure = case.find("failure")
    assert failure is not None
    assert "MISSING_FIELD" in failure.text
    assert "body.name" in failure.text
    assert "body.id" in failure.attrib.get("message", "") or "body.id" in failure.text


def test_junit_skipped_carries_the_reason(capsys, spec_path, start_server):
    url = start_server(drift=False)
    _, xml = run(capsys, spec_path, "--url", url, "--format", "junit")
    root = ET.fromstring(xml)
    case = next(c for c in root.findall(".//testcase")
                if c.get("name") == "GET /owners/{ownerId}")
    skipped = case.find("skipped")
    assert skipped is not None
    assert "ownerId" in skipped.get("message")


def test_junit_warnings_go_to_system_out(capsys, spec_path, start_server):
    url = start_server(drift=True)
    _, xml = run(capsys, spec_path, "--url", url, "--format", "junit")
    root = ET.fromstring(xml)
    case = next(c for c in root.findall(".//testcase")
                if c.get("name") == "GET /pets/{petId}")
    system_out = case.find("system-out")
    assert system_out is not None
    assert "UNDOCUMENTED_FIELD" in system_out.text


def test_junit_suite_counts_match_the_report(capsys, spec_path, start_server):
    url = start_server(drift=True)
    _, xml = run(capsys, spec_path, "--url", url, "--format", "junit")
    root = ET.fromstring(xml)
    suite = root.find(".//testsuite")
    assert root.get("tests") == "5"
    assert root.get("failures") == "2"  # /pets/{petId} and /stats drift
    assert root.get("skipped") == "1"   # /owners/{ownerId} has no value
    assert suite.get("tests") == "5" and suite.get("failures") == "2"


def test_junit_match_is_a_clean_suite(capsys, spec_path, start_server):
    url = start_server(drift=False)
    code, xml = run(capsys, spec_path, "--url", url, "--param", "ownerId=1",
                    "--format", "junit")
    assert code == 0
    root = ET.fromstring(xml)
    assert root.get("failures") == "0"
    assert root.findall(".//failure") == []


def test_junit_error_operation_is_a_failure():
    report = Report(results=[op("GET", "/x", error="request failed: timed out")])
    xml = render_junit(report, "s.yaml", "http://127.0.0.1:1")
    root = ET.fromstring(xml)
    failure = root.find(".//failure")
    assert failure is not None and "timed out" in failure.text


def test_junit_never_prints_header_values(capsys, spec_path, start_server):
    url = start_server(drift=True)
    _, xml = run(capsys, spec_path, "--url", url, "--format", "junit",
                 "-H", "Authorization: Bearer secret-token-abc123")
    ET.fromstring(xml)  # still valid XML
    assert "secret-token-abc123" not in xml