"""Fahrplan 1: the openapi version field is validated and reported."""
import json

import pytest

from specsentinel.cli import main
from specsentinel.spec import SpecError, load_spec


def write_spec(tmp_path, body):
    path = tmp_path / "spec.yaml"
    path.write_text(body)
    return str(path)


VALID = """\
openapi: %s
info: {title: t, version: '1'}
paths: {}
"""


def test_valid_openapi_3_versions_are_accepted(tmp_path):
    for version in ("3.0.0", "3.0.3", "3.1.0"):
        spec = load_spec(write_spec(tmp_path, VALID % version))
        assert spec["openapi"] == version


def test_openapi_99_0_is_rejected(tmp_path):
    with pytest.raises(SpecError, match="Unsupported OpenAPI version 99.0"):
        load_spec(write_spec(tmp_path, VALID % "99.0"))


def test_openapi_missing_version_is_rejected(tmp_path):
    with pytest.raises(SpecError, match="no 'openapi' or 'swagger' field"):
        load_spec(write_spec(tmp_path, "info: {title: t, version: '1'}\npaths: {}\n"))


def test_openapi_2_0_is_rejected(capsys, tmp_path):
    path = write_spec(tmp_path, VALID % '2.0')
    code = main([path, "--url", "http://127.0.0.1:9", "--timeout", "2"])
    assert code == 2
    err = capsys.readouterr().err
    assert "Unsupported OpenAPI version 2.0" in err
    assert "Traceback" not in err


def test_json_output_reports_openapi_version(capsys, spec_path, start_server):
    url = start_server(drift=False)
    code = main([spec_path, "--url", url, "--param", "ownerId=1", "--format", "json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["openapi_version"] == "3.0.3"