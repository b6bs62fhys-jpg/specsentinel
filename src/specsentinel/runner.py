"""Build requests from the spec, send them, and collect the results."""
from __future__ import annotations

import fnmatch
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from . import __version__
from .checker import ERROR, WARNING, Finding, check_response
from .spec import RefLoadError, SpecError, deref, iter_get_operations

_MISSING = object()


def _matches_any(patterns: list[str], path: str) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def is_selected(path: str, include: list[str], exclude: list[str]) -> bool:
    """A path is checked when it matches include (if any) and no exclude."""
    if include and not _matches_any(include, path):
        return False
    if exclude and _matches_any(exclude, path):
        return False
    return True


class Skip(Exception):
    """This operation cannot be requested automatically."""


@dataclass
class OperationResult:
    method: str
    path: str
    status: int | None = None
    findings: list[Finding] = field(default_factory=list)
    baselined: list[Finding] = field(default_factory=list)  # accepted, from the baseline
    skipped: str | None = None
    error: str | None = None  # request could not be completed

    def has_drift(self, strict: bool) -> bool:
        for f in self.findings:
            if f.severity == ERROR or (strict and f.severity == WARNING):
                return True
        return False


@dataclass
class Report:
    results: list[OperationResult]
    strict: bool = False
    baseline_loaded: bool = False
    fixed: list[dict] = field(default_factory=list)

    @property
    def baselined_count(self) -> int:
        return sum(len(r.baselined) for r in self.results)

    @property
    def checked(self) -> list[OperationResult]:
        return [r for r in self.results if r.skipped is None and r.error is None]

    @property
    def skipped(self) -> list[OperationResult]:
        return [r for r in self.results if r.skipped is not None]

    @property
    def failed(self) -> list[OperationResult]:
        return [r for r in self.results if r.error is not None]

    @property
    def drifted(self) -> list[OperationResult]:
        return [r for r in self.checked if r.has_drift(self.strict)]

    def exit_code(self) -> int:
        if self.drifted:
            return 1
        if self.failed or not self.checked:
            return 2  # the check itself could not be completed
        return 0


# --------------------------------------------------------------------------
# request building
# --------------------------------------------------------------------------

def _example_value(spec: dict, param: dict):
    if "example" in param:
        return param["example"]
    examples = param.get("examples")
    if isinstance(examples, dict) and examples:
        first = deref(spec, next(iter(examples.values())))
        if isinstance(first, dict) and "value" in first:
            return first["value"]
    schema = deref(spec, param.get("schema") or {})
    if isinstance(schema, dict):
        for key in ("example", "default"):
            if key in schema:
                return schema[key]
        if schema.get("enum"):
            return schema["enum"][0]
    return _MISSING


def _as_text(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _collect_parameters(spec: dict, path_item: dict, operation: dict) -> list[dict]:
    merged: dict[tuple, dict] = {}
    for raw in (path_item.get("parameters") or []) + (operation.get("parameters") or []):
        param = deref(spec, raw)
        if isinstance(param, dict) and "name" in param and "in" in param:
            merged[(param["in"], param["name"])] = param  # operation level wins
    return list(merged.values())


def build_request(spec: dict, base_url: str, path: str, path_item: dict,
                  operation: dict, overrides: dict[str, str]) -> tuple[str, dict]:
    target_path = path
    query: dict = {}
    headers: dict = {}

    for param in _collect_parameters(spec, path_item, operation):
        location, name = param["in"], param["name"]
        value = overrides.get(name, _MISSING)
        if value is _MISSING:
            value = _example_value(spec, param)
        if value is _MISSING:
            if location == "path" or param.get("required"):
                raise Skip(f"no example value for {location} parameter '{name}' "
                           f"(pass --param {name}=VALUE or use --params-file)")
            continue
        if location == "path":
            target_path = target_path.replace("{" + name + "}",
                                              urllib.parse.quote(_as_text(value), safe=""))
        elif location == "query":
            query[name] = [_as_text(v) for v in value] if isinstance(value, list) else _as_text(value)
        elif location == "header":
            headers[name] = _as_text(value)

    if "{" in target_path:
        raise Skip("path still contains an unresolved template variable")

    url = base_url.rstrip("/") + target_path
    if query:
        url += "?" + urllib.parse.urlencode(query, doseq=True)
    return url, headers


# --------------------------------------------------------------------------
# sending
# --------------------------------------------------------------------------

def fetch(url: str, headers: dict, timeout: float) -> tuple[int, dict, bytes]:
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:  # 4xx and 5xx still carry a response
        return exc.code, dict(exc.headers), exc.read()


def run_check(spec: dict, base_url: str, *, extra_headers: dict | None = None,
              overrides: dict[str, str] | None = None,
              defaults: dict | None = None,
              per_operation: dict[str, dict] | None = None,
              include: list[str] | None = None,
              exclude: list[str] | None = None,
              timeout: float = 10.0, strict: bool = False) -> Report:
    """Check every GET operation.

    Parameter values are taken in this order, later wins:
    spec example, defaults (params file), per_operation (params file), overrides (--param).

    ``include`` and ``exclude`` are path patterns with ``*`` as a wildcard.
    Operations that do not match are reported as SKIPPED and do not affect the
    exit code.
    """
    results: list[OperationResult] = []
    overrides = overrides or {}
    defaults = defaults or {}
    per_operation = per_operation or {}
    include = include or []
    exclude = exclude or []

    for path, path_item, operation in iter_get_operations(spec):
        result = OperationResult(method="GET", path=path)
        results.append(result)
        if not is_selected(path, include, exclude):
            result.skipped = "excluded"
            continue
        merged = {**defaults, **per_operation.get(f"GET {path}", {}), **overrides}
        try:
            url, param_headers = build_request(spec, base_url, path, path_item,
                                               operation, merged)
        except Skip as skip:
            result.skipped = str(skip)
            continue
        except RefLoadError as exc:
            result.error = f"spec problem: {exc}"
            continue
        except SpecError as exc:
            result.skipped = f"spec problem: {exc}"
            continue

        headers = {
            "User-Agent": f"SpecSentinel/{__version__}",
            "Accept": "application/json, */*;q=0.5",
        }
        headers.update(param_headers)
        headers.update(extra_headers or {})

        try:
            status, response_headers, body = fetch(url, headers, timeout)
        except Exception as exc:  # connection refused, DNS, timeout, TLS
            reason = getattr(exc, "reason", exc)
            result.error = f"request failed: {reason}"
            continue

        result.status = status
        try:
            result.findings = check_response(spec, operation, status, response_headers, body)
        except RefLoadError as exc:
            result.error = f"spec problem: {exc}"
            result.status = None
        except SpecError as exc:
            result.skipped = f"spec problem: {exc}"
            result.status = None

    return Report(results=results, strict=strict)
