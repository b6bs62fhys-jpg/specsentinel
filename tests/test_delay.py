"""--delay waits between two requests, and only between them."""
import time

from specsentinel.cli import main

SPEC_TWO = (
    "openapi: 3.0.3\n"
    "info: {title: t, version: '1'}\n"
    "paths:\n"
    "  /health:\n"
    "    get:\n"
    "      responses:\n"
    "        '200':\n"
    "          description: ok\n"
    "          content:\n"
    "            application/json:\n"
    "              schema: {type: object}\n"
    "  /pets:\n"
    "    get:\n"
    "      responses:\n"
    "        '200':\n"
    "          description: ok\n"
    "          content:\n"
    "            application/json:\n"
    "              schema: {type: array, items: {type: object}}\n"
)

SPEC_ONE = (
    "openapi: 3.0.3\n"
    "info: {title: t, version: '1'}\n"
    "paths:\n"
    "  /health:\n"
    "    get:\n"
    "      responses:\n"
    "        '200':\n"
    "          description: ok\n"
    "          content:\n"
    "            application/json:\n"
    "              schema: {type: object}\n"
)


def test_delay_is_waited_between_two_requests(tmp_path, start_server):
    spec = tmp_path / "spec.yaml"
    spec.write_text(SPEC_TWO)
    url = start_server(drift=False)
    started = time.monotonic()
    code = main([str(spec), "--url", url, "--delay", "0.2"])
    elapsed = time.monotonic() - started
    assert code == 0
    assert elapsed >= 0.19
    assert elapsed < 2.0


def test_delay_does_not_wait_before_the_first_request(tmp_path, start_server):
    spec = tmp_path / "spec.yaml"
    spec.write_text(SPEC_ONE)
    url = start_server(drift=False)
    started = time.monotonic()
    code = main([str(spec), "--url", url, "--delay", "0.5"])
    elapsed = time.monotonic() - started
    assert code == 0
    assert elapsed < 0.4
