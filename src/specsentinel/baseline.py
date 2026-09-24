"""Read and write baseline files that record accepted findings.

A baseline lets a project adopt SpecSentinel without going red on drift it
already knows about. Findings are matched by method, path, code and location,
never by the message text, so rewording a message does not invalidate a
baseline.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .runner import Report

REQUIRED_FIELDS = ("method", "path", "code", "location")


class BaselineError(Exception):
    """The baseline file is missing, unreadable or malformed."""


def entry_key(entry: dict[str, str]) -> tuple[str, str, str, str]:
    return (entry["method"], entry["path"], entry["code"], entry["location"])


def _clean(entry: dict[str, Any]) -> dict[str, str]:
    return {
        "method": entry["method"],
        "path": entry["path"],
        "code": entry["code"],
        "location": entry["location"],
        "severity": entry.get("severity", ""),
    }


def load_baseline(path: str) -> list[dict[str, str]]:
    """Load a baseline file. Raises BaselineError with a clear reason."""
    file = Path(path)
    if not file.is_file():
        raise BaselineError(f"Baseline file not found: {path}")
    try:
        text = file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise BaselineError(f"Baseline file {path} could not be read: {exc}") from exc
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise BaselineError(f"Baseline file {path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise BaselineError(
            f"Baseline file {path} must be a JSON object with a 'findings' list (in the top level)."
        )
    if not isinstance(data.get("findings"), list):
        raise BaselineError(
            f"Baseline file {path} must be a JSON object with a 'findings' list (in findings)."
        )
    entries = []
    for index, item in enumerate(data["findings"]):
        if not isinstance(item, dict):
            raise BaselineError(
                f"Baseline file {path}: every finding must be an object with the string fields "
                f"method, path, code and location (in findings[{index}])."
            )
        for field in REQUIRED_FIELDS:
            if not isinstance(item.get(field), str):
                raise BaselineError(
                    f"Baseline file {path}: every finding needs the string fields "
                    f"method, path, code and location (in findings[{index}].{field})."
                )
        entries.append(_clean(item))
    return entries


def collect_entries(report: Report) -> list[dict[str, str]]:
    """Every finding of the run, new and already baselined."""
    entries = []
    for result in report.results:
        for finding in list(result.findings) + list(result.baselined):
            entries.append({
                "method": result.method,
                "path": result.path,
                "code": finding.code,
                "location": finding.location,
                "severity": finding.severity,
            })
    entries.sort(key=lambda e: (e["method"], e["path"], e["code"], e["location"]))
    return entries


def write_baseline(path: str, entries: list[dict[str, str]]) -> None:
    payload = {"findings": entries}
    try:
        Path(path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        raise BaselineError(f"Could not write baseline file {path}: {exc}") from exc


def apply_baseline(report: Report, entries: list[dict[str, str]]) -> None:
    """Move findings that are in the baseline out of the drift path.

    Known findings end up in ``OperationResult.baselined`` and no longer affect
    the exit code. Baseline entries whose operation was checked but whose
    finding no longer occurs are recorded as ``fixed``.
    """
    known = {entry_key(entry) for entry in entries}
    report.baseline_loaded = True

    for result in report.results:
        kept = []
        for finding in result.findings:
            key = (result.method, result.path, finding.code, finding.location)
            if key in known:
                result.baselined.append(finding)
            else:
                kept.append(finding)
        result.findings = kept

    present = {
        (r.method, r.path, f.code, f.location)
        for r in report.results
        for f in r.baselined
    }
    checked = {(r.method, r.path) for r in report.checked}
    seen: set[tuple[str, str, str, str]] = set()
    fixed: list[dict[str, str]] = []
    for entry in entries:
        key = entry_key(entry)
        if key in seen:
            continue
        seen.add(key)
        if key in present:
            continue
        if (entry["method"], entry["path"]) in checked:
            fixed.append(entry)
    report.fixed = fixed
