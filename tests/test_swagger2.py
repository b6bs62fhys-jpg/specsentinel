"""Swagger 2.0 documents are translated into the internal OpenAPI 3 shape."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from specsentinel.cli import main
from specsentinel.spec import SpecError, load_spec

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "swagger2.yaml"


def write_spec(tmp_path, body):
    path = tmp_path / "swagger.yaml"
    path.write_text(body)
    return str(path)


@pytest.fixture
def start_payload_server():
    servers = []

    def _start(payload):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                body = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_address[1]}"

    yield _start
    for server in servers:
        server.shutdown()
        server.server_close()


TWO_PATHS = """\
swagger: "2.0"
info: {title: t, version: '1'}
produces:
  - application/json
paths:
  /health:
    get:
      responses:
        '200':
          description: ok
          schema: {type: object}
  /broken:
    get:
%s"""


def test_the_swagger2_example_reports_drift(start_server, capsys):
    url = start_server(drift=True)
    code = main([str(EXAMPLE), "--url", url, "--format", "json"])
    assert code == 1
    data = json.loads(capsys.readouterr().out)
    states = {op["path"]: op["state"] for op in data["operations"]}
    assert states["/health"] == "OK"
    assert states["/pets/{petId}"] == "DRIFT"
    assert states["/stats"] == "DRIFT"


def test_the_swagger2_example_matches_a_conforming_server(start_server):
    url = start_server(drift=False)
    assert main([str(EXAMPLE), "--url", url]) == 0


def test_swagger_version_is_reported_as_swagger_2_0(start_server, capsys):
    url = start_server(drift=False)
    code = main([str(EXAMPLE), "--url", url, "--format", "json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["openapi_version"] == "swagger 2.0"


def test_definitions_become_components_schemas():
    spec = load_spec(str(EXAMPLE))
    assert "definitions" not in spec
    pet = spec["components"]["schemas"]["Pet"]
    assert pet["required"] == ["id", "name"]
    items = spec["paths"]["/pets"]["get"]["responses"]["200"]["content"]
    assert items["application/json"]["schema"]["items"]["$ref"] == "#/components/schemas/Pet"


def test_response_reference_is_rewritten(tmp_path):
    spec = load_spec(write_spec(tmp_path, """\
swagger: "2.0"
info: {title: t, version: '1'}
produces: [application/json]
paths:
  /thing:
    get:
      responses:
        '404':
          $ref: '#/responses/NotFound'
responses:
  NotFound:
    description: not found
    schema: {type: object}
"""))
    assert "NotFound" in spec["components"]["responses"]
    ref = spec["paths"]["/thing"]["get"]["responses"]["404"]["$ref"]
    assert ref == "#/components/responses/NotFound"


def test_path_query_and_header_parameters_are_translated(tmp_path):
    spec = load_spec(write_spec(tmp_path, """\
swagger: "2.0"
info: {title: t, version: '1'}
produces: [application/json]
paths:
  /pets/{petId}:
    get:
      parameters:
        - {name: petId, in: path, required: true, type: integer, example: 1}
        - {name: q, in: query, type: string}
        - {name: X-Tenant, in: header, type: string}
      responses:
        '200':
          description: ok
          schema: {type: object}
"""))
    params = {p["name"]: p for p in spec["paths"]["/pets/{petId}"]["get"]["parameters"]}
    assert params["petId"]["in"] == "path"
    assert params["petId"]["schema"]["type"] == "integer"
    assert params["petId"]["example"] == 1
    assert params["q"]["in"] == "query"
    assert params["X-Tenant"]["in"] == "header"


def test_operation_produces_xml_and_json_is_checked(tmp_path, start_server):
    spec = write_spec(tmp_path, """\
swagger: "2.0"
info: {title: t, version: '1'}
produces: [application/json]
paths:
  /health:
    get:
      produces:
        - application/xml
        - application/json
      responses:
        '200':
          description: ok
          schema:
            type: object
            required: [status]
            properties:
              status: {type: string}
""")
    url = start_server(drift=False)
    assert main([spec, "--url", url]) == 0
    translated = load_spec(spec)
    content = translated["paths"]["/health"]["get"]["responses"]["200"]["content"]
    assert set(content) == {"application/xml", "application/json"}
    assert content["application/xml"]["schema"]["required"] == ["status"]


def test_operation_produces_xml_and_json_reports_drift(tmp_path, start_server, capsys):
    spec = write_spec(tmp_path, """\
swagger: "2.0"
info: {title: t, version: '1'}
produces: [application/json]
paths:
  /health:
    get:
      produces:
        - application/xml
        - application/json
      responses:
        '200':
          description: ok
          schema:
            type: object
            required: [status, missing]
            properties:
              status: {type: string}
              missing: {type: string}
""")
    url = start_server(drift=False)
    code = main([spec, "--url", url, "--format", "json"])
    assert code == 1
    data = json.loads(capsys.readouterr().out)
    health = next(op for op in data["operations"] if op["path"] == "/health")
    assert health["state"] == "DRIFT"
    assert any(f["code"] == "MISSING_FIELD" for f in health["findings"])


def test_document_produces_xml_and_json_is_checked(tmp_path, start_server):
    spec = write_spec(tmp_path, """\
swagger: "2.0"
info: {title: t, version: '1'}
produces:
  - application/xml
  - application/json
paths:
  /health:
    get:
      responses:
        '200':
          description: ok
          schema:
            type: object
            required: [status]
            properties:
              status: {type: string}
""")
    url = start_server(drift=False)
    assert main([spec, "--url", url]) == 0
    translated = load_spec(spec)
    content = translated["paths"]["/health"]["get"]["responses"]["200"]["content"]
    assert set(content) == {"application/xml", "application/json"}


def test_type_file_is_skipped(tmp_path, start_server, capsys):
    spec = write_spec(tmp_path, TWO_PATHS % """\
      responses:
        '200':
          description: ok
          schema: {type: file}
""")
    url = start_server(drift=False)
    code = main([spec, "--url", url, "--format", "json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    broken = next(op for op in data["operations"] if op["path"] == "/broken")
    assert broken["state"] == "SKIPPED"
    assert "file" in broken["skipped"]


def test_body_parameter_is_skipped(tmp_path, start_server, capsys):
    spec = write_spec(tmp_path, TWO_PATHS % """\
      parameters:
        - {name: filter, in: body, schema: {type: object}}
      responses:
        '200':
          description: ok
          schema: {type: object}
""")
    url = start_server(drift=False)
    code = main([spec, "--url", url, "--format", "json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    broken = next(op for op in data["operations"] if op["path"] == "/broken")
    assert broken["state"] == "SKIPPED"
    assert "body" in broken["skipped"]


def test_missing_produces_defaults_to_json(tmp_path):
    spec = load_spec(write_spec(tmp_path, """\
swagger: "2.0"
info: {title: t, version: '1'}
paths:
  /health:
    get:
      responses:
        '200':
          description: ok
          schema: {type: object}
"""))
    content = spec["paths"]["/health"]["get"]["responses"]["200"]["content"]
    assert "application/json" in content


def test_a_single_non_json_media_type_is_kept(tmp_path):
    spec = load_spec(write_spec(tmp_path, """\
swagger: "2.0"
info: {title: t, version: '1'}
produces: [text/plain]
paths:
  /health:
    get:
      responses:
        '200':
          description: ok
          schema: {type: object}
"""))
    content = spec["paths"]["/health"]["get"]["responses"]["200"]["content"]
    assert "text/plain" in content


def test_the_skipped_operation_stays_in_the_document(tmp_path):
    spec = load_spec(write_spec(tmp_path, TWO_PATHS % """\
      responses:
        '200':
          description: ok
          schema: {type: file}
"""))
    assert "/broken" in spec["paths"]
    assert spec["paths"]["/broken"]["get"] == {}
    assert "file" in spec._skip_reasons["/broken"]


def test_another_swagger_version_is_rejected(tmp_path):
    path = write_spec(tmp_path, """\
swagger: "1.2"
info: {title: t, version: '1'}
paths: {}
""")
    with pytest.raises(SpecError, match="Only Swagger 2.0"):
        load_spec(path)


def test_x_nullable_with_null_is_not_an_error(tmp_path, start_payload_server):
    spec = write_spec(tmp_path, """\
swagger: "2.0"
info: {title: t, version: '1'}
produces: [application/json]
paths:
  /result:
    get:
      responses:
        '200':
          description: ok
          schema:
            type: object
            required: [name]
            properties:
              name: {type: string, x-nullable: true}
""")
    url = start_payload_server({"name": None})
    assert main([spec, "--url", url]) == 0
    translated = load_spec(spec)
    name = translated["paths"]["/result"]["get"]["responses"]["200"]["content"]
    assert name["application/json"]["schema"]["properties"]["name"]["nullable"] is True


def test_without_x_nullable_null_is_still_an_error(tmp_path, start_payload_server, capsys):
    spec = write_spec(tmp_path, """\
swagger: "2.0"
info: {title: t, version: '1'}
produces: [application/json]
paths:
  /result:
    get:
      responses:
        '200':
          description: ok
          schema:
            type: object
            required: [name]
            properties:
              name: {type: string}
""")
    url = start_payload_server({"name": None})
    code = main([spec, "--url", url, "--format", "json"])
    assert code == 1
    data = json.loads(capsys.readouterr().out)
    result = next(op for op in data["operations"] if op["path"] == "/result")
    assert result["state"] == "DRIFT"
    assert any(f["code"] == "TYPE_MISMATCH" for f in result["findings"])


def test_x_nullable_nested_in_items(tmp_path, start_payload_server):
    spec = write_spec(tmp_path, """\
swagger: "2.0"
info: {title: t, version: '1'}
produces: [application/json]
paths:
  /result:
    get:
      responses:
        '200':
          description: ok
          schema:
            type: array
            items:
              type: object
              required: [tag]
              properties:
                tag: {type: string, x-nullable: true}
""")
    url = start_payload_server([{"tag": None}])
    assert main([spec, "--url", url]) == 0
    translated = load_spec(spec)
    items = translated["paths"]["/result"]["get"]["responses"]["200"]["content"]
    prop = items["application/json"]["schema"]["items"]["properties"]["tag"]
    assert prop["nullable"] is True


def test_x_nullable_in_a_definitions_ref(tmp_path, start_payload_server):
    spec = write_spec(tmp_path, """\
swagger: "2.0"
info: {title: t, version: '1'}
produces: [application/json]
paths:
  /result:
    get:
      responses:
        '200':
          description: ok
          schema:
            $ref: '#/definitions/Thing'
definitions:
  Thing:
    type: object
    required: [name]
    properties:
      name: {type: string, x-nullable: true}
""")
    url = start_payload_server({"name": None})
    assert main([spec, "--url", url]) == 0
    translated = load_spec(spec)
    name = translated["components"]["schemas"]["Thing"]["properties"]["name"]
    assert name["nullable"] is True


def test_text_output_notes_skipped_operations(spec_path, start_server, capsys):
    url = start_server(drift=False)
    code = main([spec_path, "--url", url, "--exclude", "/health"])
    out = capsys.readouterr().out
    assert code == 0
    assert "3 checked, 0 with drift, 2 skipped, 0 failed" in out
    assert "Skipped operations were not checked." in out
    assert out.index("Skipped operations were not checked.") > out.index("3 checked")
    assert "Result: MATCH" in out


def test_text_output_has_no_skip_line_when_nothing_is_skipped(spec_path, start_server,
                                                              capsys):
    url = start_server(drift=False)
    code = main([spec_path, "--url", url, "--param", "ownerId=1"])
    out = capsys.readouterr().out
    assert code == 0
    assert "0 skipped" in out
    assert "Skipped operations were not checked." not in out
