"""Path and query parameter values fall back to example, then default, then enum."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from specsentinel.runner import run_check
from specsentinel.spec import load_spec


@pytest.fixture
def echo_server():
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            seen.append(self.path)
            body = json.dumps({"path": self.path}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}", seen
    server.shutdown()
    server.server_close()


def spec_text(paths_yaml, *, swagger: bool = False) -> str:
    header = 'swagger: "2.0"' if swagger else "openapi: 3.0.3"
    return (
        f"{header}\n"
        "info: {title: t, version: '1'}\n"
        "paths:\n" + paths_yaml
    )


def ok(name: str, schema: str) -> str:
    return (
        f"  /{name}/{{v}}:\n"
        "    get:\n"
        "      parameters:\n"
        f"        - {{name: v, in: path, required: true, {schema}}}\n"
        "      responses:\n"
        "        '200': {description: ok, content: {application/json: {schema: {type: object}}}}\n"
    )


def test_param_level_example_is_used(tmp_path, echo_server):
    url, seen = echo_server
    tmp_path.joinpath("s.yaml").write_text(
        spec_text(ok("ex", "example: 3, schema: {type: integer}")))
    run_check(load_spec(str(tmp_path / "s.yaml")), url)
    assert seen == ["/ex/3"]


def test_schema_example_is_used(tmp_path, echo_server):
    url, seen = echo_server
    tmp_path.joinpath("s.yaml").write_text(
        spec_text(ok("ex", "schema: {type: integer, example: 4}")))
    run_check(load_spec(str(tmp_path / "s.yaml")), url)
    assert seen == ["/ex/4"]


def test_schema_default_is_used(tmp_path, echo_server):
    url, seen = echo_server
    tmp_path.joinpath("s.yaml").write_text(
        spec_text(ok("def", "schema: {type: integer, default: 5}")))
    run_check(load_spec(str(tmp_path / "s.yaml")), url)
    assert seen == ["/def/5"]


def test_first_enum_value_is_used(tmp_path, echo_server):
    url, seen = echo_server
    tmp_path.joinpath("s.yaml").write_text(
        spec_text(ok("en", "schema: {type: string, enum: [alpha, beta]}")))
    run_check(load_spec(str(tmp_path / "s.yaml")), url)
    assert seen == ["/en/alpha"]


def test_example_beats_default_and_enum(tmp_path, echo_server):
    url, seen = echo_server
    tmp_path.joinpath("s.yaml").write_text(
        spec_text(ok("prec", "schema: {type: integer, example: 1, default: 2, enum: [3, 4]}")))
    run_check(load_spec(str(tmp_path / "s.yaml")), url)
    assert seen == ["/prec/1"]


def test_default_beats_enum(tmp_path, echo_server):
    url, seen = echo_server
    tmp_path.joinpath("s.yaml").write_text(
        spec_text(ok("defprec", "schema: {type: integer, default: 2, enum: [3, 4]}")))
    run_check(load_spec(str(tmp_path / "s.yaml")), url)
    assert seen == ["/defprec/2"]


def test_overrides_beat_spec_values(tmp_path, echo_server):
    url, seen = echo_server
    tmp_path.joinpath("s.yaml").write_text(
        spec_text(ok("override", "schema: {type: integer, default: 5}")))
    run_check(load_spec(str(tmp_path / "s.yaml")), url, overrides={"v": "9"})
    assert seen == ["/override/9"]


def test_parameter_without_a_value_is_skipped(tmp_path, echo_server):
    url, seen = echo_server
    paths = (
        "  /none/{v}:\n"
        "    get:\n"
        "      parameters:\n"
        "        - {name: v, in: path, required: true, schema: {type: integer}}\n"
        "      responses:\n"
        "        '200': {description: ok, content: {application/json: {schema: {type: object}}}}\n"
    )
    tmp_path.joinpath("s.yaml").write_text(spec_text(paths))
    report = run_check(load_spec(str(tmp_path / "s.yaml")), url)
    assert seen == []
    assert report.results[0].skipped is not None
    assert "no example value for path parameter 'v'" in report.results[0].skipped


def test_swagger2_default_is_used(tmp_path, echo_server):
    url, seen = echo_server
    paths = (
        "  /swdef/{v}:\n"
        "    get:\n"
        "      parameters:\n"
        "        - {name: v, in: path, required: true, type: integer, default: 5}\n"
        "      responses:\n"
        "        '200':\n"
        "          description: ok\n"
        "          schema: {type: object}\n"
    )
    tmp_path.joinpath("s.yaml").write_text(spec_text(paths, swagger=True))
    run_check(load_spec(str(tmp_path / "s.yaml")), url)
    assert seen == ["/swdef/5"]


def test_swagger2_first_enum_value_is_used(tmp_path, echo_server):
    url, seen = echo_server
    paths = (
        "  /swen/{v}:\n"
        "    get:\n"
        "      parameters:\n"
        "        - {name: v, in: path, required: true, type: string, enum: [bb, cc]}\n"
        "      responses:\n"
        "        '200':\n"
        "          description: ok\n"
        "          schema: {type: object}\n"
    )
    tmp_path.joinpath("s.yaml").write_text(spec_text(paths, swagger=True))
    run_check(load_spec(str(tmp_path / "s.yaml")), url)
    assert seen == ["/swen/bb"]


def test_swagger2_parameter_without_a_value_is_skipped(tmp_path, echo_server):
    url, seen = echo_server
    paths = (
        "  /swnone/{v}:\n"
        "    get:\n"
        "      parameters:\n"
        "        - {name: v, in: path, required: true, type: integer}\n"
        "      responses:\n"
        "        '200':\n"
        "          description: ok\n"
        "          schema: {type: object}\n"
    )
    tmp_path.joinpath("s.yaml").write_text(spec_text(paths, swagger=True))
    report = run_check(load_spec(str(tmp_path / "s.yaml")), url)
    assert seen == []
    assert "no example value for path parameter 'v'" in report.results[0].skipped