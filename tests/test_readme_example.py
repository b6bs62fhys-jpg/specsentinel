"""The README shows real output, not made up output.

The excerpt at the top of the README and the full output under "Install and
first run" are compared with a real run against the demo API in examples/.
Only the port in the Target line is normalised, because the test lets the OS
pick a free one.
"""
import re
from pathlib import Path

from specsentinel.cli import main

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")


def _real_output(capsys, monkeypatch, start_server) -> str:
    monkeypatch.chdir(ROOT)
    url = start_server(drift=True)
    code = main(["examples/petstore.yaml", "--url", url])
    assert code == 1
    out = capsys.readouterr().out
    return re.sub(r"http://127\.0\.0\.1:\d+", "http://127.0.0.1:8099", out)


def _code_blocks(text: str) -> list[str]:
    return re.findall(r"```[a-z]*\n(.*?)```", text, flags=re.S)


def test_first_ten_lines_say_what_for_whom_and_show_an_example():
    head = "\n".join(README.splitlines()[:10])
    assert "checks a running API against its OpenAPI" in head
    assert "for teams" in head
    assert "$ specsentinel examples/petstore.yaml --url http://127.0.0.1:8099" in head
    assert "Result: DRIFT (exit code 1)" in head


def test_top_excerpt_is_taken_from_a_real_run(capsys, monkeypatch, start_server):
    real = _real_output(capsys, monkeypatch, start_server).splitlines()
    excerpt = _code_blocks(README)[0].splitlines()
    assert excerpt[0].startswith("$ specsentinel ")
    position = 0
    for line in excerpt[1:]:
        if line == "[...]":
            continue
        assert line in real[position:], f"README line not in the real output (in this order): {line!r}"
        position = real.index(line, position) + 1


def test_full_output_in_readme_matches_a_real_run(capsys, monkeypatch, start_server):
    real = _real_output(capsys, monkeypatch, start_server)
    marker = "The demo drifts on purpose. Real output:"
    assert marker in README
    block = _code_blocks(README.split(marker, 1)[1])[0]
    assert block == real
