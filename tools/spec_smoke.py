"""Smoke test the SpecSentinel checker against a real OpenAPI description.

For every GET operation and every documented JSON response, a conforming
example is generated from the response schema and fed through the checker.
A conforming example must produce no findings. Any finding is therefore either
a bug in the checker, a weakness of this generator, or a real inconsistency
inside the spec, and is listed so it can be looked at by hand.

This verifies the comparison logic. It does not replace a run against a live API.

Usage: python tools/spec_smoke.py <path or URL to an OpenAPI file>
"""
from __future__ import annotations

import json
import sys
from collections import Counter

from specsentinel.checker import ERROR, check_response, validate_value
from specsentinel.spec import deref, iter_get_operations, load_spec

MAX_DEPTH = 60  # hard stop, cycles are cut earlier through the $ref chain
MAX_REF_REPEAT = 2  # how often one $ref may repeat inside itself


def _first_type(schema: dict):
    t = schema.get("type")
    if isinstance(t, list):
        non_null = [x for x in t if x != "null"]
        return non_null[0] if non_null else "null"
    return t


def _minimal(spec: dict, schema, depth: int):
    """Smallest value that is plausible for the schema. Used when recursion is cut off."""
    schema = deref(spec, schema)
    if not isinstance(schema, dict):
        return None
    if schema.get("enum"):
        return schema["enum"][0]
    t = _first_type(schema)
    if t == "object" or (t is None and "properties" in schema):
        return {}
    if t == "array":
        return []
    return {"string": "x", "integer": 1, "number": 1.5, "boolean": True}.get(t)


def generate(spec: dict, schema, depth: int = 0, refs: tuple = ()):
    """Build an example value for a schema.

    Recursive schemas are cut through the chain of $ref targets: once a target
    repeats inside itself, only required properties are generated.
    """
    lean = False
    hops = 0
    while isinstance(schema, dict) and "$ref" in schema:
        ref = schema["$ref"]
        if refs.count(ref) >= MAX_REF_REPEAT:
            return _minimal(spec, deref(spec, schema), depth)
        lean = lean or refs.count(ref) >= 1
        refs = refs + (ref,)
        schema = deref(spec, {"$ref": ref})
        hops += 1
        if hops > 50:
            return None
    if not isinstance(schema, dict):
        return None
    if depth > MAX_DEPTH:
        return _minimal(spec, schema, depth)
    if schema.get("enum"):
        return schema["enum"][0]
    if "const" in schema:
        return schema["const"]

    if "allOf" in schema:
        merged = {k: v for k, v in schema.items() if k != "allOf"}
        props = dict(merged.get("properties") or {})
        required = list(merged.get("required") or [])
        for part in schema["allOf"]:
            part = deref(spec, part)
            if not isinstance(part, dict):
                continue
            props.update(part.get("properties") or {})
            required += part.get("required") or []
            for key in ("type", "items", "enum"):
                if key in part and key not in merged:
                    merged[key] = part[key]
        merged["properties"] = props
        merged["required"] = required
        return generate(spec, merged, depth + 1, refs)

    for key in ("oneOf", "anyOf"):
        if schema.get(key):
            best = None
            for alternative in schema[key]:
                candidate = generate(spec, alternative, depth + 1, refs)
                if best is None:
                    best = candidate
                problems = [f for f in validate_value(spec, alternative, candidate, "body")
                            if f.severity == ERROR]
                if not problems:
                    return candidate
            return best

    t = _first_type(schema)
    if t is None:
        t = "object" if "properties" in schema else ("array" if "items" in schema else None)
    if t == "object":
        required = set(schema.get("required") or [])
        out = {}
        for name, sub in (schema.get("properties") or {}).items():
            if lean and name not in required:
                continue
            out[name] = generate(spec, sub, depth + 1, refs)
        for name in required:
            out.setdefault(name, None)
        return out
    if t == "array":
        item = generate(spec, schema.get("items") or {}, depth + 1, refs)
        return [] if item is None else [item]
    if t == "string":
        fmt = schema.get("format")
        return {"date-time": "2020-01-01T00:00:00Z", "date": "2020-01-01",
                "uri": "https://example.com", "email": "a@example.com",
                "uuid": "00000000-0000-0000-0000-000000000000"}.get(fmt, "x")
    if t == "integer":
        return int(schema["minimum"]) if schema.get("minimum") is not None else 1
    if t == "number":
        return float(schema["minimum"]) if schema.get("minimum") is not None else 1.5
    if t == "boolean":
        return True
    return None


def status_for(key) -> int:
    key = str(key)
    if key.lower() == "default":
        return 418  # not documented explicitly, so it falls through to default
    if key.upper().endswith("XX"):
        return int(key[0]) * 100
    return int(key)


def run(source: str) -> dict:
    spec = load_spec(source)
    result = {"operations": 0, "checked": 0, "flagged": 0, "crashes": 0,
              "codes": Counter(), "samples": []}
    for path, _item, operation in iter_get_operations(spec):
        result["operations"] += 1
        for status, response in deref(spec, operation.get("responses") or {}).items():
            try:
                response = deref(spec, response)
                for media, body_spec in (response.get("content") or {}).items():
                    if "json" not in media.lower() or "schema" not in body_spec:
                        continue
                    result["checked"] += 1
                    body = json.dumps(generate(spec, body_spec["schema"])).encode()
                    findings = [f for f in check_response(
                        spec, operation, status_for(status),
                        {"content-type": media}, body) if f.severity == ERROR]
                    if findings:
                        result["flagged"] += 1
                        for f in findings:
                            result["codes"][f.code] += 1
                        if len(result["samples"]) < 10:
                            f = findings[0]
                            result["samples"].append(
                                f"{path} [{status}] {f.code} at {f.location}: {f.message}")
            except Exception as exc:  # a crash is a result, not a reason to stop
                result["crashes"] += 1
                if len(result["samples"]) < 10:
                    result["samples"].append(f"{path} [{status}] CRASH {type(exc).__name__}: {exc}")
    return result


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    try:
        r = run(argv[1])
    except Exception as exc:
        print(f"could not load spec: {exc}")
        return 2
    print(f"Spec:                {argv[1]}")
    print(f"GET operations:      {r['operations']}")
    print(f"JSON responses:      {r['checked']}")
    print(f"Responses flagged:   {r['flagged']}")
    print(f"Crashes:             {r['crashes']}")
    if r["codes"]:
        print(f"Finding codes:       {dict(r['codes'])}")
    for line in r["samples"]:
        print("  " + line)
    return 0 if r["crashes"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))