"""Loading an OpenAPI document and resolving local references."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import yaml


class SpecError(Exception):
    """The spec could not be loaded or understood."""


def load_spec(source: str) -> dict:
    if source.startswith(("http://", "https://")):
        try:
            with urllib.request.urlopen(source, timeout=20) as response:
                text = response.read().decode("utf-8")
        except Exception as exc:  # network errors are reported, not raised raw
            raise SpecError(f"Could not download spec from {source}: {exc}") from exc
    else:
        path = Path(source)
        if not path.is_file():
            raise SpecError(f"Spec file not found: {source}")
        text = path.read_text(encoding="utf-8")

    try:
        data = json.loads(text)
    except ValueError:
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise SpecError(f"Spec is neither valid JSON nor valid YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise SpecError("Spec is not an OpenAPI document.")
    if "swagger" in data:
        raise SpecError("Swagger 2.0 is not supported. Use an OpenAPI 3.x document.")
    if "openapi" not in data:
        raise SpecError("Spec has no 'openapi' field. Is this an OpenAPI 3.x document?")
    return data


def resolve_ref(spec: dict, ref: str):
    if not ref.startswith("#/"):
        raise SpecError(f"Only local references are supported, got: {ref}")
    node = spec
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            raise SpecError(f"Reference could not be resolved: {ref}")
        node = node[part]
    return node


def deref(spec: dict, node):
    """Follow $ref chains until a real object is reached."""
    hops = 0
    while isinstance(node, dict) and "$ref" in node:
        hops += 1
        if hops > 50:
            raise SpecError("Reference cycle detected.")
        node = resolve_ref(spec, node["$ref"])
    return node


def iter_get_operations(spec: dict):
    """Yield (path, path_item, operation) for every GET operation.

    SpecSentinel only sends GET requests. Mutating methods could change data
    on the API under test, so they are out of scope on purpose.
    """
    for path, item in (spec.get("paths") or {}).items():
        item = deref(spec, item)
        if isinstance(item, dict) and isinstance(item.get("get"), dict):
            yield path, item, item["get"]
