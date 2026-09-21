"""External $ref resolution: files, fragments, relative paths and URLs."""
import http.server
import threading

import pytest

from specsentinel.checker import validate_value
from specsentinel.cli import main as cli_main
from specsentinel.spec import SpecError, deref, load_spec

MAIN = """\
openapi: 3.0.3
info: {title: api, version: "1"}
paths:
  /pets:
    get:
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: "pets.yaml#/components/schemas/Pet"
"""

PETS = """\
components:
  schemas:
    Pet:
      type: object
      required: [id, name]
      properties:
        id: {type: integer}
        name: {type: string}
"""

PETS_LOCAL_REF = """\
components:
  schemas:
    Pet:
      $ref: "#/components/schemas/Owner"
    Owner:
      type: object
      required: [id]
      properties:
        id: {type: integer}
"""

MAIN_NESTED = """\
openapi: 3.0.3
info: {title: api, version: "1"}
paths:
  /x:
    get:
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                $ref: "parts/pet.yaml#/components/schemas/Pet"
"""

MAIN_MISSING_OPERATION = """\
openapi: 3.0.3
info: {title: api, version: "1"}
paths:
  /pets:
    get:
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: "missing.yaml#/components/schemas/Pet"
"""

MAIN_MISSING_PATH_ITEM = """\
openapi: 3.0.3
info: {title: api, version: "1"}
paths:
  /pets:
    $ref: "missing.yaml#/paths/~1pets"
"""


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_cross_file_ref_with_fragment(tmp_path):
    _write(tmp_path, "pets.yaml", PETS)
    spec = load_spec(str(_write(tmp_path, "main.yaml", MAIN)))
    ref = {"$ref": "pets.yaml#/components/schemas/Pet"}
    assert validate_value(spec, ref, {"id": 1, "name": "Rex"}, "body") == []
    codes = [f.code for f in validate_value(spec, ref, {"id": 1}, "body")]
    assert codes == ["MISSING_FIELD"]


def test_local_ref_inside_external_file_resolves_against_that_file(tmp_path):
    _write(tmp_path, "pets.yaml", PETS_LOCAL_REF)
    spec = load_spec(str(_write(tmp_path, "main.yaml", MAIN)))
    ref = {"$ref": "pets.yaml#/components/schemas/Pet"}
    assert validate_value(spec, ref, {"id": 1}, "body") == []
    codes = [f.code for f in validate_value(spec, ref, {}, "body")]
    assert codes == ["MISSING_FIELD"]
    assert all("body.id" == f.location for f in validate_value(spec, ref, {}, "body"))


def test_relative_refs_resolve_from_the_document_that_holds_them(tmp_path):
    _write(tmp_path, "base.yaml", "components:\n"
                                   "  schemas:\n"
                                   "    Base:\n"
                                   "      type: object\n"
                                   "      required: [id]\n"
                                   "      properties:\n"
                                   "        id: {type: integer}\n")
    _write(tmp_path, "parts/pet.yaml",
           'components:\n'
           '  schemas:\n'
           '    Pet:\n'
           '      $ref: "../base.yaml#/components/schemas/Base"\n')
    spec = load_spec(str(_write(tmp_path, "main.yaml", MAIN_NESTED)))
    ref = {"$ref": "parts/pet.yaml#/components/schemas/Pet"}
    assert validate_value(spec, ref, {"id": 1}, "body") == []
    assert [f.code for f in validate_value(spec, ref, {}, "body")] == ["MISSING_FIELD"]


def test_whole_document_reference(tmp_path):
    _write(tmp_path, "pets.yaml", PETS)
    spec = load_spec(str(_write(tmp_path, "main.yaml", MAIN)))
    node = deref(spec, {"$ref": "pets.yaml"})
    assert isinstance(node, dict) and "components" in node
    assert isinstance(node["components"], dict)


def test_file_reference_cycle_is_reported_not_crashing(tmp_path):
    _write(tmp_path, "a.yaml",
           'components:\n'
           '  schemas:\n'
           '    X:\n'
           '      $ref: "b.yaml#/components/schemas/Y"\n')
    _write(tmp_path, "b.yaml",
           'components:\n'
           '  schemas:\n'
           '    Y:\n'
           '      $ref: "a.yaml#/components/schemas/X"\n')
    spec = load_spec(str(_write(tmp_path, "main.yaml", MAIN)))
    with pytest.raises(SpecError, match="[Cc]ycle"):
        deref(spec, {"$ref": "a.yaml#/components/schemas/X"})


def test_path_item_reference_cycle_gives_exit_code_2(capsys, tmp_path):
    _write(tmp_path, "a.yaml",
           'paths:\n'
           '  /x:\n'
           '    $ref: "b.yaml#/paths/~1x"\n')
    _write(tmp_path, "b.yaml",
           'paths:\n'
           '  /x:\n'
           '    $ref: "a.yaml#/paths/~1x"\n')
    main = ("openapi: 3.0.3\n"
            "info: {title: api, version: \"1\"}\n"
            "paths:\n"
            "  /x:\n"
            "    $ref: \"a.yaml#/paths/~1x\"\n")
    spec_path = _write(tmp_path, "main.yaml", main)
    code, out = run(capsys, str(spec_path), "--url", "http://127.0.0.1:1", "--timeout", "2")
    assert code == 2
    assert out.out or out.err
    assert "cycle" in (out.out + out.err).lower()


def test_missing_external_file_gives_exit_code_2(capsys, tmp_path, start_server):
    url = start_server(drift=False)
    spec_path = _write(tmp_path, "main.yaml", MAIN_MISSING_OPERATION)
    code, out = run(capsys, str(spec_path), "--url", url)
    assert code == 2
    assert "not found" in out.out
    assert "INCOMPLETE" in out.out


def test_missing_external_file_in_path_item_gives_exit_code_2(capsys, tmp_path):
    spec_path = _write(tmp_path, "main.yaml", MAIN_MISSING_PATH_ITEM)
    code, out = run(capsys, str(spec_path), "--url", "http://127.0.0.1:1", "--timeout", "2")
    assert code == 2
    assert "not found" in out.err


def test_relative_refs_for_url_loaded_spec(tmp_path):
    _write(tmp_path, "pets.yaml", PETS)
    _write(tmp_path, "main.yaml", MAIN)

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            path = tmp_path / self.path.lstrip("/")
            if path.is_file():
                body = path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        spec = load_spec(f"{base}/main.yaml")
        ref = {"$ref": "pets.yaml#/components/schemas/Pet"}
        assert validate_value(spec, ref, {"id": 1, "name": "Rex"}, "body") == []
    finally:
        server.shutdown()
        server.server_close()


def run(capsys, *args):
    code = cli_main(list(args))
    return code, capsys.readouterr()