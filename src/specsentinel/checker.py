"""Compare one live HTTP response with the OpenAPI operation that describes it."""
from __future__ import annotations

import json
from dataclasses import dataclass

from .spec import deref

ERROR = "error"
WARNING = "warning"

MAX_ARRAY_ITEMS = 20  # items checked per array, keeps output and runtime small


@dataclass(frozen=True)
class Finding:
    severity: str  # "error" or "warning"
    code: str      # stable identifier, e.g. MISSING_FIELD
    location: str  # where in the response, e.g. body.pets[].name
    message: str


# --------------------------------------------------------------------------
# type helpers
# --------------------------------------------------------------------------

def type_of(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):  # bool is a subclass of int, check it first
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def type_matches(expected: str, value) -> bool:
    actual = type_of(value)
    if expected == actual:
        return True
    if expected == "number" and actual == "integer":
        return True
    if expected == "integer" and actual == "number":
        return float(value).is_integer()
    return False


def enum_contains(options: list, value) -> bool:
    return any(type_of(o) == type_of(value) and o == value for o in options)


# --------------------------------------------------------------------------
# schema handling
# --------------------------------------------------------------------------

def flatten_all_of(spec: dict, schema, depth: int = 0) -> dict:
    """Merge allOf members into one schema so extra field detection is correct."""
    schema = deref(spec, schema)
    if not isinstance(schema, dict):
        return {}
    if "allOf" not in schema or depth > 20:
        return schema

    merged = {k: v for k, v in schema.items() if k != "allOf"}
    properties = dict(merged.get("properties") or {})
    required = list(merged.get("required") or [])
    for member in schema["allOf"] or []:
        flat = flatten_all_of(spec, member, depth + 1)
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


def _error_count(findings: list[Finding]) -> int:
    return sum(1 for f in findings if f.severity == ERROR)


def _describe_types(types: list[str]) -> str:
    return " or ".join(types)


def validate_value(spec: dict, schema, value, path: str, depth: int = 0) -> list[Finding]:
    """Validate a JSON value against a schema. Returns findings, never raises."""
    if depth > 40:
        return []
    schema = flatten_all_of(spec, schema)
    if not schema:
        return []

    out: list[Finding] = []

    # oneOf / anyOf: the value has to fit at least one alternative
    alternatives = schema.get("oneOf") or schema.get("anyOf")
    if alternatives:
        best: list[Finding] | None = None
        matched = False
        for alt in alternatives:
            result = validate_value(spec, alt, value, path, depth + 1)
            if _error_count(result) == 0:
                out.extend(result)
                matched = True
                break
            if best is None or _error_count(result) < _error_count(best):
                best = result
        if not matched:
            out.append(Finding(ERROR, "NO_SCHEMA_MATCH", path,
                               "value matches none of the oneOf/anyOf alternatives in the spec"))
            out.extend(best or [])

    # type
    declared = schema.get("type")
    types: list[str] | None
    if isinstance(declared, str):
        types = [declared]
    elif isinstance(declared, list):
        types = [t for t in declared if isinstance(t, str)]
    elif "properties" in schema:
        types = ["object"]
    elif "items" in schema:
        types = ["array"]
    else:
        types = None

    if value is None:
        if schema.get("nullable") is True or types is None or "null" in types:
            return out
        out.append(Finding(ERROR, "TYPE_MISMATCH", path,
                           f"expected {_describe_types(types)}, got null"))
        return out

    if types is not None:
        concrete = [t for t in types if t != "null"]
        if concrete and not any(type_matches(t, value) for t in concrete):
            out.append(Finding(ERROR, "TYPE_MISMATCH", path,
                               f"expected {_describe_types(concrete)}, got {type_of(value)}"))
            return out

    if isinstance(schema.get("enum"), list) and not enum_contains(schema["enum"], value):
        out.append(Finding(ERROR, "ENUM_MISMATCH", path,
                           f"value {json.dumps(value)} is not one of {json.dumps(schema['enum'])}"))

    if isinstance(value, dict):
        out.extend(_validate_object(spec, schema, value, path, depth))
    elif isinstance(value, list):
        items = schema.get("items")
        if items:
            for item in value[:MAX_ARRAY_ITEMS]:
                out.extend(validate_value(spec, items, item, f"{path}[]", depth + 1))

    return out


def _validate_object(spec: dict, schema: dict, value: dict, path: str, depth: int) -> list[Finding]:
    out: list[Finding] = []
    properties = schema.get("properties") or {}
    required = schema.get("required") or []
    additional = schema.get("additionalProperties", True)

    for name in required:
        if name not in value:
            out.append(Finding(ERROR, "MISSING_FIELD", f"{path}.{name}",
                               "required field is missing in the response"))

    for name, item in value.items():
        child = f"{path}.{name}"
        if name in properties:
            out.extend(validate_value(spec, properties[name], item, child, depth + 1))
        elif additional is False:
            out.append(Finding(ERROR, "UNDOCUMENTED_FIELD", child,
                               "field is returned but the spec forbids additional properties"))
        elif isinstance(additional, dict) and additional:
            out.extend(validate_value(spec, additional, item, child, depth + 1))
        elif properties:
            # free form objects (no properties listed) are not reported
            out.append(Finding(WARNING, "UNDOCUMENTED_FIELD", child,
                               "field is returned but not described in the spec"))
    return out


# --------------------------------------------------------------------------
# response level checks
# --------------------------------------------------------------------------

def match_response(responses: dict, status: int):
    """Find the documented response for a status: exact, then 2XX style, then default."""
    keys = {str(k).upper(): v for k, v in (responses or {}).items()}
    for candidate in (str(status), f"{status // 100}XX", "DEFAULT"):
        if candidate in keys:
            return keys[candidate]
    return None


def pick_media_type(content: dict, content_type: str):
    main = content_type.split(";")[0].strip().lower()
    for key in content:
        if key.lower() == main:
            return key
    for key in content:
        lowered = key.lower()
        if lowered == "*/*":
            return key
        if lowered.endswith("/*") and main.startswith(lowered[:-1]):
            return key
    return None


def check_response(spec: dict, operation: dict, status: int,
                   headers: dict, body: bytes) -> list[Finding]:
    """Return every difference between the live response and the operation's spec."""
    responses = deref(spec, operation.get("responses") or {})
    documented = match_response(responses, status)

    if documented is None:
        listed = ", ".join(sorted(str(k) for k in responses)) or "none"
        return [Finding(ERROR, "UNDOCUMENTED_STATUS", "status",
                        f"status {status} is not documented (documented: {listed})")]

    documented = deref(spec, documented)
    content = documented.get("content") or {}
    if not content or status in (204, 304):
        return []

    lowered = {str(k).lower(): v for k, v in headers.items()}
    content_type = lowered.get("content-type", "")

    if not content_type:
        if not body:
            return [Finding(ERROR, "EMPTY_BODY", "body",
                            "the spec documents a response body but the response was empty")]
        return [Finding(ERROR, "CONTENT_TYPE_MISSING", "header.Content-Type",
                        "response has a body but no Content-Type header")]

    media = pick_media_type(content, content_type)
    if media is None:
        main = content_type.split(";")[0].strip()
        listed = ", ".join(content) or "none"
        return [Finding(ERROR, "UNDOCUMENTED_CONTENT_TYPE", "header.Content-Type",
                        f"content type {main} is not documented (documented: {listed})")]

    if "json" not in media.lower():
        return []  # only JSON bodies are compared in this version

    try:
        data = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return [Finding(ERROR, "INVALID_JSON", "body",
                        "response is declared as JSON but the body is not valid JSON")]

    media_object = deref(spec, content[media]) or {}
    schema = media_object.get("schema") if isinstance(media_object, dict) else None
    if not schema:
        return []

    findings = validate_value(spec, schema, data, "body")
    return list(dict.fromkeys(findings))  # drop duplicates, keep order
