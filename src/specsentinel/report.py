"""Render a Report as text or JSON."""
from __future__ import annotations

import json

from . import __version__
from .checker import ERROR, WARNING
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
    if report.skipped:
        lines.append("Skipped operations were not checked.")
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


def render_junit(report: Report, spec_source: str, base_url: str) -> str:
    """Render the report as JUnit XML, one testcase per operation.

    Drift and failed requests are ``failure``, skipped operations are
    ``skipped`` with their reason, warnings are collected as ``system-out``.
    Attribute and text content never include request headers or their values.
    """
    if not report.results:
        return '<?xml version="1.0" encoding="utf-8"?>\n<testsuites tests="0" ' \
               'failures="0" errors="0" skipped="0"/>\n'

    cases: list[str] = []
    for result in report.results:
        name = f"{result.method} {result.path}"
        opening = f'<testcase classname="SpecSentinel" name="{_escape(name)}">'
        if result.skipped is not None:
            cases.append(f'{opening}<skipped message="{_escape(result.skipped)}"/>'
                         "</testcase>")
            continue

        warnings = [f for f in result.findings if f.severity == WARNING]
        system_out = ""
        if warnings:
            lines = "\n".join(f"{f.code} at {f.location}: {f.message}" for f in warnings)
            system_out = f"<system-out>{_escape(lines)}</system-out>"

        if result.error is not None:
            cases.append(f'{opening}<failure message="{_escape(result.error)}">'
                         f"{_escape(result.error)}</failure>{system_out}</testcase>")
        elif result.has_drift(report.strict):
            errors = [f for f in result.findings if f.severity == ERROR]
            details = "\n".join(f"{f.code} at {f.location}" for f in errors) or "drift"
            if errors:
                message = f"{len(errors)} finding(s): {errors[0].code} at {errors[0].location}"
            else:
                message = "drift"
            cases.append(f'{opening}<failure message="{_escape(message)}">'
                         f"{_escape(details)}</failure>{system_out}</testcase>")
        else:
            cases.append(f"{opening}{system_out}</testcase>")

    tests = len(report.results)
    failures = sum(1 for r in report.results
                   if r.error is not None or r.has_drift(report.strict))
    skipped = len(report.skipped)
    suite = (
        f'<testsuites name="SpecSentinel" tests="{tests}" failures="{failures}" '
        f'errors="0" skipped="{skipped}">'
        f'<testsuite name="specsentinel" tests="{tests}" failures="{failures}" '
        f'errors="0" skipped="{skipped}" time="0">'
    )
    return ('<?xml version="1.0" encoding="utf-8"?>\n' + suite + "\n"
            + "\n".join(cases) + "\n</testsuite></testsuites>\n")


def _escape(text) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&apos;"))


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
