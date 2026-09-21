"""Render a Report as text or JSON."""
from __future__ import annotations

import json

from . import __version__
from .runner import Report


def _state(result, strict: bool) -> str:
    if result.skipped is not None:
        return "SKIPPED"
    if result.error is not None:
        return "FAILED"
    return "DRIFT" if result.has_drift(strict) else "OK"


def render_text(report: Report, spec_source: str, base_url: str) -> str:
    lines = [f"SpecSentinel {__version__}", f"Spec:   {spec_source}", f"Target: {base_url}", ""]

    width = max((len(f"{r.method} {r.path}") for r in report.results), default=10)
    for r in report.results:
        label = f"{r.method} {r.path}".ljust(width)
        status = str(r.status) if r.status is not None else "-"
        lines.append(f"{label}  {status.ljust(3)}  {_state(r, report.strict)}")
        if r.skipped:
            lines.append(f"    {r.skipped}")
        if r.error:
            lines.append(f"    {r.error}")
        for f in r.findings:
            lines.append(f"    {f.severity.ljust(7)} {f.code.ljust(24)} {f.location}")
            lines.append(f"            {f.message}")

    if report.fixed:
        lines.append("")
        lines.append("Baseline findings that no longer occur (fixed):")
        for entry in report.fixed:
            lines.append(f"    {entry['code'].ljust(24)} {entry['method']} {entry['path']}  {entry['location']}")

    lines.append("")
    summary = (
        f"{len(report.checked)} checked, {len(report.drifted)} with drift, "
        f"{len(report.skipped)} skipped, {len(report.failed)} failed"
    )
    if report.baseline_loaded:
        summary += f", {report.baselined_count} baselined"
    lines.append(summary)
    code = report.exit_code()
    verdict = {0: "MATCH", 1: "DRIFT", 2: "INCOMPLETE"}[code]
    lines.append(f"Result: {verdict} (exit code {code})")
    return "\n".join(lines)


def _severity_counts(report: Report) -> dict:
    counts = {"error": 0, "warning": 0}
    for result in report.results:
        for finding in result.findings:
            counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return counts


def render_json(report: Report, spec_source: str, base_url: str) -> str:
    payload = {
        "version": __version__,
        "spec": spec_source,
        "target": base_url,
        "strict": report.strict,
        "exit_code": report.exit_code(),
        "summary": {
            "checked": len(report.checked),
            "drift": len(report.drifted),
            "skipped": len(report.skipped),
            "failed": len(report.failed),
            "counts": _severity_counts(report),
            "baselined": report.baselined_count,
        },
        "findings": [
            {"code": f.code, "method": r.method, "path": r.path, "severity": f.severity}
            for r in report.results
            for f in r.findings
        ],
        "fixed": [
            {"code": e["code"], "method": e["method"], "path": e["path"],
             "location": e["location"], "severity": e["severity"]}
            for e in report.fixed
        ],
        "operations": [
            {
                "method": r.method,
                "path": r.path,
                "status": r.status,
                "state": _state(r, report.strict),
                "skipped": r.skipped,
                "error": r.error,
                "baselined": len(r.baselined),
                "findings": [
                    {"severity": f.severity, "code": f.code,
                     "location": f.location, "message": f.message}
                    for f in r.findings
                ],
            }
            for r in report.results
        ],
    }
    return json.dumps(payload, indent=2)
