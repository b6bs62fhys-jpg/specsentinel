"""Job summary and annotations for the SpecSentinel GitHub Action.

Reads the text report of a SpecSentinel run and its exit code, writes a short
Markdown summary to $GITHUB_STEP_SUMMARY and prints one annotation per
operation with drift (or one for a run that could not be completed).

Standard library only, because the action may install any SpecSentinel
version. The text report format ("GET /path  200  DRIFT") is the same in every
released version. This script never decides the result: it always exits 0 and
the action passes on SpecSentinel's own exit code.
"""
from __future__ import annotations

import os
import re
import sys
from typing import Mapping, Optional

_OPERATION = re.compile(r"^([A-Z]+) (\S+)\s+(\S+)\s+(OK|DRIFT|SKIPPED|FAILED)\s*$")
_COUNTS = re.compile(r"^\d+ checked, .*$")
_VERDICT = {0: "No drift (exit code 0)", 1: "Drift found (exit code 1)", 2: "Check could not be completed (exit code 2)"}


def _escape_data(value: str) -> str:
    """Escape a workflow command message (GitHub Actions rules)."""
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A").replace("::", "%3A%3A")


def _operations(text: str) -> list[tuple[str, str, str, str]]:
    return [m.groups() for m in map(_OPERATION.match, text.splitlines()) if m]  # type: ignore[misc]


def annotation_lines(text: str, code: int) -> list[str]:
    """One annotation per drifting or failed operation; one for exit code 2."""
    if code == 2:
        return ["::error title=SpecSentinel::The check could not be completed (exit code 2)."]
    lines = []
    for method, path, status, state in _operations(text):
        if state == "DRIFT":
            message = f"{method} {path} returned {status} and does not match the spec."
            lines.append(f"::error title=SpecSentinel drift::{_escape_data(message)}")
        elif state == "FAILED":
            message = f"{method} {path} could not be checked."
            lines.append(f"::warning title=SpecSentinel::{_escape_data(message)}")
    return lines


def _cell(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def _fence(text: str) -> str:
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def markdown(text: str, code: int) -> str:
    """Short Markdown summary: verdict, counts, operations with drift, full report."""
    parts = ["## SpecSentinel", "", f"**{_VERDICT.get(code, f'exit code {code}')}**", ""]
    counts = next((line for line in text.splitlines() if _COUNTS.match(line)), None)
    if counts:
        parts += [counts, ""]
    notable = [op for op in _operations(text) if op[3] in ("DRIFT", "FAILED")]
    if notable:
        parts += ["| Operation | Status | Result |", "|---|---|---|"]
        parts += [f"| {_cell(m)} {_cell(p)} | {_cell(s)} | {st} |" for m, p, s, st in notable]
        parts.append("")
    fence = _fence(text)
    parts += ["<details><summary>Full report</summary>", "", fence + "text", text.rstrip(), fence, "", "</details>", ""]
    return "\n".join(parts)


def main(argv: list[str], env: Optional[Mapping[str, str]] = None) -> int:
    env = os.environ if env is None else env
    try:
        report_path, code_text = argv[0], argv[1]
        code = int(code_text)
        with open(report_path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except (IndexError, ValueError, OSError):
        return 0
    for line in annotation_lines(text, code):
        print(line)
    target = env.get("GITHUB_STEP_SUMMARY")
    if target:
        try:
            with open(target, "a", encoding="utf-8") as handle:
                handle.write(markdown(text, code))
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
