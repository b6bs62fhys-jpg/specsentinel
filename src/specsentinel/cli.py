"""Command line entry point."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from . import __version__
from .baseline import (
    BaselineError,
    apply_baseline,
    collect_entries,
    load_baseline,
    write_baseline,
)
from .report import render_json, render_text
from .runner import run_check
from .spec import SpecError, load_spec


def _one_line(text) -> str:
    """Collapse any exception text to a single line, so errors stay readable."""
    return " ".join(str(text).split())


def _fatal(message, fmt: str) -> int:
    """Print a fatal error and return exit code 2.

    The human readable message always goes to stderr. In JSON mode a small
    object goes to stdout as well, so a machine can read the failure.
    """
    text = _one_line(message)
    print(f"specsentinel: {text}", file=sys.stderr)
    if fmt == "json":
        print(json.dumps({"exit_code": 2, "error": text}, indent=2))
    return 2


def _nothing_checked_message(report, base_url: str) -> str:
    if report.failed:
        reason = report.failed[0].error or "unknown error"
        if reason.startswith("spec problem"):
            return f"nothing could be checked: {reason}."
        return (f"could not check any operation at {base_url}: {reason}. "
                "Check --url, the scheme and host, and that the API is reachable.")
    if report.skipped:
        return f"nothing could be checked: {report.skipped[0].skipped}."
    return "the spec has no GET operations to check."


def _should_collapse(report) -> bool:
    """True when nothing was checked and a one line error is clearer than a report.

    When every failure is a spec problem (a bad reference, for example) the
    report is kept, because it points at the operation that failed.
    """
    if report.checked:
        return False
    if report.failed and all((r.error or "").startswith("spec problem")
                             for r in report.failed):
        return False
    return True


def _parse_headers(values: list[str]) -> dict:
    headers = {}
    for raw in values:
        if ":" not in raw:
            raise ValueError(f"Invalid header '{raw}'. Use the form 'Name: value'.")
        name, _, value = raw.partition(":")
        headers[name.strip()] = value.strip()
    return headers


def _parse_params(values: list[str]) -> dict:
    params = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"Invalid parameter '{raw}'. Use the form NAME=VALUE.")
        name, _, value = raw.partition("=")
        params[name.strip()] = value
    return params


def _load_params_file(path: str) -> tuple[dict, dict]:
    """Read a params file. Returns (defaults, per_operation).

    Plain entries apply to every operation that has a parameter of that name.
    Entries whose key starts with "GET " apply to that one operation only.
    """
    file = Path(path)
    if not file.is_file():
        raise ValueError(f"Params file not found: {path}")
    text = file.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except ValueError:
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ValueError(f"Params file is not valid JSON or YAML: {exc}") from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("Params file must be a mapping of parameter names to values.")

    defaults: dict = {}
    per_operation: dict = {}
    for key, value in data.items():
        if isinstance(value, dict) and str(key).strip().upper().startswith("GET "):
            label = "GET " + str(key).strip()[4:].strip()
            per_operation[label] = {str(n): v for n, v in value.items()}
        else:
            defaults[str(key)] = value
    return defaults, per_operation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="specsentinel",
        description="Compare a running API with its OpenAPI spec and report drift. "
                    "Exit code 0 means they match, 1 means drift, 2 means the check "
                    "could not be completed.",
    )
    parser.add_argument("spec", help="path or URL of the OpenAPI 3.x document (YAML or JSON)")
    parser.add_argument("--url", required=True, help="base URL of the running API")
    parser.add_argument("-H", "--header", action="append", default=[], metavar="'Name: value'",
                        help="header sent with every request, repeatable (for example auth)")
    parser.add_argument("--param", action="append", default=[], metavar="NAME=VALUE",
                        help="value for a path or query parameter, repeatable")
    parser.add_argument("--params-file", metavar="FILE",
                        help="YAML or JSON file with parameter values (see README)")
    parser.add_argument("--include", action="append", default=[], metavar="PATTERN",
                        help="check only paths matching PATTERN, repeatable, * is a wildcard")
    parser.add_argument("--exclude", action="append", default=[], metavar="PATTERN",
                        help="skip paths matching PATTERN, repeatable, * is a wildcard")
    parser.add_argument("--baseline", metavar="FILE",
                        help="ignore findings recorded in FILE, so only new drift fails")
    parser.add_argument("--write-baseline", metavar="FILE",
                        help="write all current findings to FILE as a JSON baseline")
    parser.add_argument("--timeout", type=float, default=10.0,
                        help="seconds to wait per request (default 10)")
    parser.add_argument("--delay", type=float, default=0.0,
                        help="seconds to wait between requests (default 0)")
    parser.add_argument("--strict", action="store_true",
                        help="treat warnings, such as undocumented fields, as drift")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default text)")
    parser.add_argument("--version", action="version", version=f"specsentinel {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        headers = _parse_headers(args.header)
        overrides = _parse_params(args.param)
        defaults, per_operation = ({}, {})
        if args.params_file:
            defaults, per_operation = _load_params_file(args.params_file)
        baseline_entries = load_baseline(args.baseline) if args.baseline else []
        spec = load_spec(args.spec)
    except (ValueError, SpecError, BaselineError) as exc:
        return _fatal(exc, args.format)

    try:
        report = run_check(spec, args.url, extra_headers=headers, overrides=overrides,
                           defaults=defaults, per_operation=per_operation,
                           include=args.include, exclude=args.exclude,
                           timeout=args.timeout, strict=args.strict,
                           delay=args.delay)
    except (ValueError, SpecError) as exc:
        return _fatal(exc, args.format)

    if args.baseline:
        apply_baseline(report, baseline_entries)

    if _should_collapse(report):
        return _fatal(_nothing_checked_message(report, args.url), args.format)

    if args.write_baseline:
        try:
            entries = collect_entries(report)
            write_baseline(args.write_baseline, entries)
        except BaselineError as exc:
            return _fatal(exc, args.format)
        if args.format == "json":
            print(json.dumps({"exit_code": 0, "baseline": args.write_baseline,
                              "findings": len(entries)}, indent=2))
        else:
            print(f"Wrote {len(entries)} findings to {args.write_baseline}")
        return 0

    render = render_json if args.format == "json" else render_text
    print(render(report, args.spec, args.url))
    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
