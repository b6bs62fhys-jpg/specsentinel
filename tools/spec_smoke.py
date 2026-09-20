"""Smoke-test the checker against a spec.

For every JSON schema of a GET response, build a schema-conforming example
body and run it through check_response. Schemas that are broken or that trip
up the checker show up as findings or crashes instead of requiring a live API.
"""
from __future__ import annotations

import json
import sys

from specsentinel.checker import ERROR, check_response, validate_value
from specsentinel.spec import SpecError, deref, iter_get_operations, load_spec

MAX_DEPTH = 25
MAX_FINDINGS_SHOWN = 10


def _scalar_value(schema: dict):
    if isinstance(schema.get("enum"), list) and schema["enum"]:
        return schema["enum"][0]
    for key in ("example", "default"):
        if key in schema:
            return schema[key]
    declared = schema.get("type")
    if isinstance(declared, list):
        declared = next((t for t in declared if t != "null"), None)
    if declared == "boolean":
        return False
    if declared == "number":
        return 1.0
    if declared == "integer":
        return 1
    if declared == "null":
        return None
    return "string"


def _minimal_value(spec: dict, schema: dict, stack: frozenset, depth: int):
    """Smallest value that is still mostly valid, used to break cycles."""
    schema = flatten(spec, schema)
    if schema.get("oneOf") or schema.get("anyOf"):
        for alt in schema.get("oneOf") or schema.get("anyOf"):
            return generate_value(spec, alt, stack, depth + 1)
    if "properties" in schema or schema.get("type") == "object":
        obj = {}
        props = schema.get("properties") or {}
        for name in schema.get("required") or []:
            prop = deref(spec, props.get(name) or {})
            if isinstance(prop, dict) and id(prop) in stack:
                continue  # cyclic property would never terminate
            obj[name] = generate_value(spec, props[name], stack, depth + 1)
        return obj
    if "items" in schema:
        return []
    return _scalar_value(schema)


def flatten(spec: dict, schema: dict) -> dict:
    """Resolve references and merge allOf, safe for the generator."""
    schema = deref(spec, schema)
    if isinstance(schema, dict):
        return _merge_all_of(spec, schema, 0)
    return {}


def _merge_all_of(spec: dict, schema: dict, depth: int) -> dict:
    if not isinstance(schema, dict) or "allOf" not in schema or depth > MAX_DEPTH:
        return schema
    merged = {k: v for k, v in schema.items() if k != "allOf"}
    properties = dict(merged.get("properties") or {})
    required = list(merged.get("required") or [])
    for member in schema["allOf"] or []:
        flat = _merge_all_of(spec, deref(spec, member), depth + 1)
        for key, val in flat.items():
            if key == "properties":
                properties.update(val)
            elif key == "required":
                required.extend(r for r in val if r not in required)
            elif key not in merged:
                merged[key] = val
    if properties:
        merged["properties"] = properties
    if required:
        merged["required"] = required
    return merged


def generate_value(spec: dict, schema, stack: frozenset = frozenset(), depth: int = 0):
    """Build a concrete value that satisfies the schema, if one exists."""
    raw = deref(spec, schema)
    if not isinstance(raw, dict):
        return None
    if depth > MAX_DEPTH or id(raw) in stack:
        return _minimal_value(spec, raw, stack, depth)  # cycle: minimal object, not null
    new_stack = stack | {id(raw)}
    schema = flatten(spec, raw)

    if schema.get("oneOf") or schema.get("anyOf"):
        best, best_value = None, None
        for alt in schema.get("oneOf") or schema.get("anyOf"):
            candidate = generate_value(spec, alt, new_stack, depth + 1)
            errors = validate_value(spec, schema, candidate, "body")
            if not any(f.severity == ERROR for f in errors):
                return candidate  # variant the schema itself accepts
            if best is None or len(errors) < len(best):
                best, best_value = errors, candidate
        return best_value

    if isinstance(schema.get("enum"), list) and schema["enum"]:
        return schema["enum"][0]
    for key in ("example", "default"):
        if key in schema:
            return schema[key]

    declared = schema.get("type")
    if isinstance(declared, list):
        declared = next((t for t in declared if t != "null"), None)

    if "properties" in schema or declared == "object":
        props = schema.get("properties") or {}
        return {name: generate_value(spec, sub, new_stack, depth + 1)
                for name, sub in props.items()}
    if "items" in schema or declared == "array":
        items = schema.get("items")
        return [generate_value(spec, items, new_stack, depth + 1)] if items else []
    if declared == "boolean":
        return False
    if declared == "number":
        return 1.0
    if declared == "integer":
        return 1
    if declared == "null":
        return None
    if declared == "string":
        return "string"
    if declared == "array":
        return []
    if declared == "object":
        return {}
    return _scalar_value(schema)


def _status_code(status_key: str) -> int:
    if status_key.isdigit():
        return int(status_key)
    return 200  # 2XX / default responses are matched against a generic success code


def smoke(spec: dict):
    get_operations = list(iter_get_operations(spec))
    checked = 0
    findings = []
    crashes = 0

    for path, _, operation in get_operations:
        responses = deref(spec, operation.get("responses") or {})
        if not isinstance(responses, dict):
            continue
        for status_key, response_raw in responses.items():
            response = deref(spec, response_raw)
            if not isinstance(response, dict):
                continue
            for media, media_raw in (response.get("content") or {}).items():
                if "json" not in media.lower():
                    continue
                media_object = deref(spec, media_raw) or {}
                schema = media_object.get("schema") if isinstance(media_object, dict) else None
                if not schema:
                    continue
                try:
                    value = generate_value(spec, schema)
                    body = json.dumps(value).encode("utf-8")
                    found = check_response(spec, operation, _status_code(str(status_key)),
                                           {"Content-Type": media}, body)
                except Exception as exc:  # a crash is a finding in itself
                    crashes += 1
                    findings.append(
                        (path, str(status_key),
                         f"crash: {type(exc).__name__}: {exc}"))
                    continue
                checked += 1
                findings.extend((path, str(status_key), f) for f in found)

    return get_operations, checked, findings, crashes


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: spec_smoke.py <openapi-file-or-url>")
        return 2
    try:
        spec = load_spec(argv[0])
    except SpecError as exc:
        print(f"error: {exc}")
        return 2

    get_operations, checked, findings, crashes = smoke(spec)

    print(f"Spec:           {argv[0]}")
    print(f"GET operations: {len(get_operations)}")
    print(f"Checked:        {checked}")
    print(f"Findings:       {len(findings)}")
    print(f"Crashes:        {crashes}")
    for path, status, detail in findings[:MAX_FINDINGS_SHOWN]:
        if isinstance(detail, str):
            print(f"GET {path}  {status}  {detail}")
        else:
            print(f"GET {path}  {status}  {detail.severity} {detail.code} "
                  f"({detail.location}): {detail.message}")

    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())