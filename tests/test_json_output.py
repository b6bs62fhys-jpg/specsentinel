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


def test_json_output_when_one_operation_fails(capsys, tmp_path):
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path == "/bad":
                self.close_connection = True  # no response, the request fails
                return
            body = b'{"status": "ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        "openapi: 3.0.3\n"
        "info: {title: t, version: '1'}\n"
        "paths:\n"
        "  /ok:\n"
        "    get:\n"
        "      responses:\n"
        "        '200':\n"
        "          description: ok\n"
        "          content:\n"
        "            application/json:\n"
        "              schema:\n"
        "                type: object\n"
        "                required: [status]\n"
        "                properties:\n"
        "                  status: {type: string}\n"
        "  /bad:\n"
        "    get:\n"
        "      responses:\n"
        "        '200': {description: ok}\n"
    )
    url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        code, data = run(capsys, str(spec), "--url", url, "--format", "json")
    finally:
        server.shutdown()
        server.server_close()
    assert code == 2
    assert data["exit_code"] == 2
    assert data["summary"]["checked"] == 1
    assert data["summary"]["failed"] == 1
    assert data["summary"]["counts"] == {"error": 0, "warning": 0}
    assert data["findings"] == []