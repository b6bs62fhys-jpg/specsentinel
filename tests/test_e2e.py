import json

from specsentinel.cli import main


def run(capsys, *args):
    code = main(list(args))
    return code, capsys.readouterr()


def test_drift_gives_exit_code_1(capsys, spec_path, start_server):
    url = start_server(drift=True)
    code, out = run(capsys, spec_path, "--url", url)
    assert code == 1
    assert "MISSING_FIELD" in out.out
    assert "TYPE_MISMATCH" in out.out
    assert "UNDOCUMENTED_STATUS" in out.out
    assert "Result: DRIFT" in out.out


def test_match_gives_exit_code_0(capsys, spec_path, start_server):
    url = start_server(drift=False)
    code, out = run(capsys, spec_path, "--url", url, "--param", "ownerId=1")
    assert code == 0
    assert "Result: MATCH" in out.out


def test_skipped_operation_does_not_fail_the_run(capsys, spec_path, start_server):
    url = start_server(drift=False)
    code, out = run(capsys, spec_path, "--url", url)  # ownerId has no example
    assert code == 0
    assert "SKIPPED" in out.out


def test_warnings_only_pass_normally_and_fail_with_strict(capsys, tmp_path, start_server):
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        "openapi: 3.0.3\n"
        "paths:\n"
        "  /pets/{petId}:\n"
        "    get:\n"
        "      parameters:\n"
        "        - {name: petId, in: path, required: true, example: 1, schema: {type: integer}}\n"
        "      responses:\n"
        "        '200':\n"
        "          description: ok\n"
        "          content:\n"
        "            application/json:\n"
        "              schema:\n"
        "                type: object\n"
        "                properties:\n"
        "                  id: {type: integer}\n"
    )
    url = start_server(drift=False)  # returns id and name and status, only id is documented
    code, _ = run(capsys, str(spec), "--url", url)
    assert code == 0
    code, out = run(capsys, str(spec), "--url", url, "--strict")
    assert code == 1
    assert "UNDOCUMENTED_FIELD" in out.out


def test_unreachable_api_gives_exit_code_2(capsys, spec_path):
    code, out = run(capsys, spec_path, "--url", "http://127.0.0.1:1", "--timeout", "2")
    assert code == 2
    assert out.out == ""
    assert "could not check any operation" in out.err


def test_missing_spec_gives_exit_code_2(capsys):
    code, out = run(capsys, "does-not-exist.yaml", "--url", "http://127.0.0.1:1")
    assert code == 2
    assert "not found" in out.err


def test_bad_header_gives_exit_code_2(capsys, spec_path):
    code, out = run(capsys, spec_path, "--url", "http://127.0.0.1:1", "-H", "nocolon")
    assert code == 2
    assert "Invalid header" in out.err


def test_json_output_is_parseable(capsys, spec_path, start_server):
    url = start_server(drift=True)
    code, out = run(capsys, spec_path, "--url", url, "--format", "json")
    data = json.loads(out.out)
    assert code == 1 and data["exit_code"] == 1
    assert data["summary"]["drift"] == 2
    codes = {f["code"] for op in data["operations"] for f in op["findings"]}
    assert {"MISSING_FIELD", "TYPE_MISMATCH", "UNDOCUMENTED_STATUS"} <= codes


def test_header_is_sent(capsys, tmp_path):
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    seen = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            seen["auth"] = self.headers.get("Authorization")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    spec = tmp_path / "s.yaml"
    spec.write_text("openapi: 3.0.3\npaths:\n  /x:\n    get:\n      responses:\n"
                    "        '200':\n          description: ok\n")
    url = f"http://127.0.0.1:{server.server_address[1]}"
    code, _ = run(capsys, str(spec), "--url", url, "-H", "Authorization: Bearer abc")
    server.shutdown()
    server.server_close()
    assert code == 0
    assert seen["auth"] == "Bearer abc"


def test_params_file_fills_in_path_parameters(capsys, spec_path, start_server, tmp_path):
    url = start_server(drift=False)
    params = tmp_path / "params.yaml"
    params.write_text("ownerId: 7\n")
    code, out = run(capsys, spec_path, "--url", url, "--params-file", str(params))
    assert code == 0
    assert "SKIPPED" not in out.out
    assert "5 checked" in out.out


def test_params_file_per_operation_and_cli_precedence(capsys, spec_path, start_server, tmp_path):
    url = start_server(drift=False)
    params = tmp_path / "params.json"
    params.write_text('{"petId": 1, "GET /pets/{petId}": {"petId": 999}}')
    # per operation value 999 makes the demo answer 404, which the spec documents
    code, out = run(capsys, spec_path, "--url", url, "--params-file", str(params),
                    "--param", "ownerId=1", "--format", "json")
    data = json.loads(out.out)
    status = {op["path"]: op["status"] for op in data["operations"]}
    assert code == 0 and status["/pets/{petId}"] == 404
    # --param beats the params file
    code, out = run(capsys, spec_path, "--url", url, "--params-file", str(params),
                    "--param", "ownerId=1", "--param", "petId=1", "--format", "json")
    status = {op["path"]: op["status"] for op in json.loads(out.out)["operations"]}
    assert status["/pets/{petId}"] == 200


def test_documented_endpoint_answering_404_is_drift(capsys, tmp_path):
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"gone")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    spec = tmp_path / "s.yaml"
    spec.write_text("openapi: 3.0.3\npaths:\n  /gone:\n    get:\n"
                    "      responses:\n"
                    "        '200':\n          description: ok\n"
                    "          content:\n"
                    "            application/json:\n"
                    "              schema: {type: object}\n")
    url = f"http://127.0.0.1:{server.server_address[1]}"
    code, out = run(capsys, str(spec), "--url", url)
    server.shutdown()
    server.server_close()
    assert code == 1
    assert "UNDOCUMENTED_STATUS" in out.out
    assert "404" in out.out


def test_endpoint_not_listed_in_spec_survives_a_run(capsys, tmp_path):
    """An endpoint the live API serves but the spec does not mention is not
    checked and does not affect the result (the model is spec-driven)."""
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    spec = tmp_path / "s.yaml"
    spec.write_text("openapi: 3.0.3\npaths:\n  /known:\n    get:\n"
                    "      responses:\n"
                    "        '200':\n          description: ok\n")
    url = f"http://127.0.0.1:{server.server_address[1]}"
    code, out = run(capsys, str(spec), "--url", url)
    server.shutdown()
    server.server_close()
    assert code == 0
    assert "/known" in out.out  # extra endpoint /unknown never requested


def test_missing_params_file_gives_exit_code_2(capsys, spec_path):
    code, out = run(capsys, spec_path, "--url", "http://127.0.0.1:1",
                    "--params-file", "nope.yaml")
    assert code == 2
    assert "Params file not found" in out.err
