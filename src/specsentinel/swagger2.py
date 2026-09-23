"""Translate a Swagger 2.0 document into the OpenAPI 3 shape used internally.

Only the parts SpecSentinel needs are translated: paths, path/query/header
parameters, responses with a schema, definitions and top level responses. The
base URL still comes from ``--url``, so ``host``, ``basePath`` and ``schemes``
are ignored. Anything that cannot be translated is reported as a skip reason
instead of raising, so a single odd operation never stops the run.
"""
from __future__ import annotations

import copy
from typing import Any, cast


_SCHEMA_KEYS = (
    "type", "format", "items", "enum", "default", "minimum", "maximum",
    "minLength", "maxLength", "pattern", "uniqueItems", "multipleOf",
    "x-nullable",
)


def translate(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """Return (openapi_document, skip_reasons) for a Swagger 2.0 document.

    ``skip_reasons`` maps a path to a clear reason. The path is still present
    in the document with a placeholder GET operation, so the runner reports it
    as SKIPPED instead of silently dropping it.
    """
    doc: dict[str, Any] = {
        "openapi": "3.0.3",
        "info": data.get("info") or {"title": "Swagger 2.0", "version": "0"},
        "paths": {},
    }
    components: dict[str, Any] = {}
    if isinstance(data.get("definitions"), dict):
        components["schemas"] = rewrite_refs(data["definitions"])
    if isinstance(data.get("responses"), dict):
        components["responses"] = rewrite_refs(data["responses"])
    if components:
        doc["components"] = components

    global_produces = data.get("produces")
    skip_reasons: dict[str, str] = {}
    for path, item in (data.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        has_get = isinstance(item.get("get"), dict)
        new_item: dict[str, Any] = {}
        path_params, reason = translate_parameters(item.get("parameters") or [])
        if reason is None and path_params:
            new_item["parameters"] = path_params
        operation = item.get("get")
        if reason is None and has_get:
            new_operation, reason = translate_operation(cast(dict[str, Any], operation),
                                                        global_produces)
            if new_operation:
                new_item["get"] = new_operation

        if reason is not None:
            if not has_get:
                continue
            skip_reasons[path] = reason
            new_item["get"] = {}
        if new_item:
            doc["paths"][path] = new_item
    return doc, skip_reasons


def translate_operation(operation: dict[str, Any], global_produces: Any
                        ) -> tuple[dict[str, Any], str | None]:
    media_types = _media_types(operation.get("produces", global_produces))
    parameters, reason = translate_parameters(operation.get("parameters") or [])
    if reason is not None:
        return {}, reason
    responses = operation.get("responses")
    if not isinstance(responses, dict):
        return {}, "Swagger 2.0 operation has no responses object"

    new_operation: dict[str, Any] = {"responses": {}}
    for key in ("summary", "description", "operationId", "tags"):
        if operation.get(key) is not None:
            new_operation[key] = operation[key]
    if parameters:
        new_operation["parameters"] = parameters
    for status, response in responses.items():
        new_response, reason = translate_response(response, media_types)
        if reason is not None:
            return {}, reason
        new_operation["responses"][str(status)] = new_response
    return new_operation, None


def translate_parameters(raw_parameters: Any) -> tuple[list[dict[str, Any]], str | None]:
    translated: list[dict[str, Any]] = []
    for raw in raw_parameters:
        if not isinstance(raw, dict):
            continue
        if "$ref" in raw:
            return [], f"Swagger 2.0 parameter reference is not supported: {raw['$ref']}"
        location = raw.get("in")
        if location not in ("path", "query", "header"):
            return [], (f"Swagger 2.0 parameter in '{location}' is not supported, "
                        "only path, query and header are")
        if raw.get("type") == "file":
            return [], "Swagger 2.0 'type: file' is not supported"
        parameter = {
            "name": raw.get("name"),
            "in": location,
            "required": bool(raw.get("required", False)),
            "schema": rewrite_refs(_schema_of(raw)),
        }
        if raw.get("description") is not None:
            parameter["description"] = raw["description"]
        if raw.get("example") is not None:
            parameter["example"] = raw["example"]
        translated.append(parameter)
    return translated, None


def translate_response(response: Any, media_types: list[str]
                       ) -> tuple[dict[str, Any], str | None]:
    if not isinstance(response, dict):
        return {}, "Swagger 2.0 response is not an object"
    if "$ref" in response:
        return {"$ref": rewrite_ref(response["$ref"])}, None
    if _contains_file(response.get("schema")):
        return {}, "Swagger 2.0 'type: file' is not supported"

    new_response: dict[str, Any] = {"description": response.get("description") or ""}
    schema = response.get("schema")
    if schema is not None:
        translated_schema = rewrite_refs(schema)
        examples = response.get("examples")
        content: dict[str, Any] = {}
        for media in media_types:
            media_object: dict[str, Any] = {"schema": translated_schema}
            if isinstance(examples, dict) and media in examples:
                media_object["example"] = examples[media]
            content[media] = media_object
        new_response["content"] = content
    headers = response.get("headers")
    if isinstance(headers, dict):
        new_headers: dict[str, Any] = {}
        for name, header in headers.items():
            if not isinstance(header, dict):
                continue
            if header.get("type") == "file":
                return {}, "Swagger 2.0 'type: file' is not supported"
            new_header: dict[str, Any] = {"schema": rewrite_refs(_schema_of(header))}
            if header.get("description") is not None:
                new_header["description"] = header["description"]
            new_headers[str(name)] = new_header
        if new_headers:
            new_response["headers"] = new_headers
    return new_response, None


def rewrite_refs(value: Any) -> Any:
    """Deep copy ``value``, rewrite ``$ref`` targets and map x-nullable to
    nullable, so every schema, nested in properties and items, is handled."""
    if isinstance(value, dict):
        if "$ref" in value and isinstance(value["$ref"], str):
            return {"$ref": rewrite_ref(value["$ref"])}
        result = {}
        for key, item in value.items():
            if key == "x-nullable":
                result["nullable"] = bool(item)
            else:
                result[key] = rewrite_refs(item)
        return result
    if isinstance(value, list):
        return [rewrite_refs(item) for item in value]
    return copy.deepcopy(value)


def rewrite_ref(ref: str) -> str:
    """Map ``#/definitions/...`` and ``#/responses/...`` to components."""
    for old, new in (("/definitions/", "/components/schemas/"),
                     ("/responses/", "/components/responses/")):
        if old in ref:
            return ref.replace(old, new)
    return ref


def _schema_of(source: dict[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(source[key]) for key in _SCHEMA_KEYS if key in source}


def _media_types(produces: Any) -> list[str]:
    if not produces:
        return ["application/json"]
    if isinstance(produces, str):
        produces = [produces]
    seen = []
    for media in produces:
        if isinstance(media, str) and media not in seen:
            seen.append(media)
    return seen or ["application/json"]


def _contains_file(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("type") == "file":
            return True
        return any(_contains_file(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_file(item) for item in value)
    return False
