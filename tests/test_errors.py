"""Every fatal error must be one clear line, no traceback, exit code 2."""
import json

from specsentinel.cli import main


def run(capsys, *args):
    code = main(list(args))
    return code, capsys.readouterr()


def assert_single_clear_line(out):
    assert "Traceback" not in out.err
    assert out.out == ""
    lines = [line for line in out.err.splitlines() if line.strip()]
    assert len(lines) == 1, out.err
    assert lines[0].startswith("specsentinel: ")


def test_spec_file_not_found(capsys):
    code, out = run(capsys, "does-not-exist.yaml", "--url", "http://127.0.0.1:1")
    assert code == 2
    assert_single_clear_line(out)
    assert "Spec file not found" in out.err


def test_invalid_yaml(capsys, tmp_path):
    spec = tmp_path / "broken.yaml"
    spec.write_text("openapi: 3.0.3\npaths: [unclosed\n")
    code, out = run(capsys, str(spec), "--url", "http://127.0.0.1:1")
    assert code == 2
    assert_single_clear_line(out)
    assert "neither valid JSON nor valid YAML" in out.err


def test_invalid_json(capsys, tmp_path):
    spec = tmp_path / "broken.json"
    spec.write_text('{"openapi": "3.0.3", "paths": {')
    code, out = run(capsys, str(spec), "--url", "http://127.0.0.1:1")
    assert code == 2
    assert_single_clear_line(out)
    assert "neither valid JSON nor valid YAML" in out.err


def test_not_an_openapi_document(capsys, tmp_path):
    spec = tmp_path / "other.yaml"
    spec.write_text("foo: bar\n")
    code, out = run(capsys, str(spec), "--url", "http://127.0.0.1:1")
    assert code == 2
    assert_single_clear_line(out)
    assert "no 'openapi' field" in out.err


def test_target_not_reachable(capsys, spec_path):
    code, out = run(capsys, spec_path, "--url", "http://127.0.0.1:1", "--timeout", "2")
    assert code == 2
    assert_single_clear_line(out)
    assert "could not check any operation" in out.err
    assert "reachable" in out.err


def test_wrong_base_url(capsys, spec_path):
    code, out = run(capsys, spec_path, "--url", "not-a-url", "--timeout", "2")
    assert code == 2
    assert_single_clear_line(out)
    assert "unknown url type" in out.err
    assert "Check --url" in out.err


def test_timeout(capsys, spec_path):
    code, out = run(capsys, spec_path, "--url", "http://10.255.255.1", "--timeout", "0.3")
    assert code == 2
    assert_single_clear_line(out)
    assert "timed out" in out.err


def test_missing_path_parameter(capsys, tmp_path, start_server):
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        "openapi: 3.0.3\n"
        "info: {title: t, version: '1'}\n"
        "paths:\n"
        "  /x/{id}:\n"
        "    get:\n"
        "      parameters:\n"
        "        - {name: id, in: path, required: true, schema: {type: integer}}\n"
        "      responses:\n"
        "        '200': {description: ok}\n"
    )
    url = start_server(drift=False)
    code, out = run(capsys, str(spec), "--url", url)
    assert code == 2
    assert_single_clear_line(out)
    assert "no example value for path parameter 'id'" in out.err
    assert "--param id=VALUE" in out.err
