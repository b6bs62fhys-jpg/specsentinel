"""Loading an OpenAPI document and resolving references.

References may stay inside the document (``#/components/schemas/Pet``) or
point at another document, optionally with a fragment
(``pets.yaml#/components/schemas/Pet``). Other documents are resolved relative
to the document that contains the reference, so a spec loaded from a file can
reference sibling files and a spec loaded from a URL can reference relative and
absolute URLs.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

URL_PREFIXES = ("http://", "https://")


class SpecError(Exception):
    """The spec could not be loaded or understood."""


class RefLoadError(SpecError):
    """A referenced document is missing, unreadable, or cannot be resolved."""


class SpecDocument(dict):
    """A loaded document that remembers its source and reference resolver."""


class _Tagged(dict):
    """A resolved reference target that knows which document it lives in.

    Without this tag a ``$ref`` inside a referenced file would wrongly be
    resolved against the root document instead of against its own file.
    """


class _Resolver:
    """Loads referenced documents on demand and caches them by canonical name."""

    def __init__(self, root: SpecDocument):
        self._cache = {_canonical(root._source): root}

    def document(self, source: str) -> SpecDocument:
        key = _canonical(source)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        doc = _load_document(key)
        doc._resolver = self
        self._cache[key] = doc
        return doc

    def resolve(self, ref: str, base: SpecDocument):
        file_part, _, fragment = ref.partition("#")
        if file_part:
            target = self.document(_join(base._source, file_part))
        else:
            target = base
        if not fragment:
            return _tagged(target, target)
        return _tagged(_navigate(target, fragment, ref), target)


def _canonical(source: str) -> str:
    if source.startswith(URL_PREFIXES):
        return source
    return str(Path(source).resolve())


def _join(base: str, ref_file: str) -> str:
    if base.startswith(URL_PREFIXES):
        return urllib.parse.urljoin(base, ref_file)
    if ref_file.startswith(URL_PREFIXES):
        return ref_file
    return str((Path(base).parent / ref_file).resolve())


def _tagged(value, doc):
    if isinstance(value, dict):
        wrapped = _Tagged(value)
        wrapped._doc = doc
        return wrapped
    return value


def _doc_of(node):
    return getattr(node, "_doc", None)


def _download(source: str, exc_type) -> str:
    try:
        with urllib.request.urlopen(source, timeout=20) as response:
            return response.read().decode("utf-8")
    except Exception as exc:  # network errors are reported, not raised raw
        raise exc_type(f"Could not load {source}: {exc}") from exc


def _parse(text: str, label: str, exc_type) -> dict:
    try:
        data = json.loads(text)
    except ValueError:
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise exc_type(f"{label} is neither valid JSON nor valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise exc_type(f"{label} is not an OpenAPI document.")
    return data


def _load_document(source: str) -> SpecDocument:
    if source.startswith(URL_PREFIXES):
        text = _download(source, RefLoadError)
    else:
        path = Path(source)
        if not path.is_file():
            raise RefLoadError(f"Referenced file not found: {source}")
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RefLoadError(f"Could not read referenced file {source}: {exc}") from exc

    doc = SpecDocument(_parse(text, f"Referenced document {source}", RefLoadError))
    doc._source = source
    return doc


def load_spec(source: str) -> SpecDocument:
    if source.startswith(URL_PREFIXES):
        text = _download(source, SpecError)
    else:
        path = Path(source)
        if not path.is_file():
            raise SpecError(f"Spec file not found: {source}")
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SpecError(f"Could not read spec file {source}: {exc}") from exc

    data = _parse(text, "Spec", SpecError)
    if "swagger" in data:
        raise SpecError("Swagger 2.0 is not supported. Use an OpenAPI 3.x document.")
    if "openapi" not in data:
        raise SpecError("Spec has no 'openapi' field. Is this an OpenAPI 3.x document?")

    doc = SpecDocument(data)
    doc._source = source
    doc._resolver = _Resolver(doc)
    return doc


def _navigate(doc: dict, fragment: str, ref: str):
    node = doc
    for part in fragment.lstrip("/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            raise RefLoadError(f"Reference could not be resolved: {ref}")
        node = node[part]
    return node


def resolve_ref(spec: dict, ref: str):
    """Resolve a local ``#/...`` reference inside the given document."""
    if not ref.startswith("#/"):
        raise SpecError(f"Only local references are supported, got: {ref}")
    return _navigate(spec, ref[1:], ref)


def deref(spec: dict, node):
    """Follow $ref chains until a real object is reached.

    Cross document references are resolved relative to the document that holds
    them. Cycles are cut off and reported instead of looping forever.
    """
    hops = 0
    while isinstance(node, dict) and "$ref" in node:
        hops += 1
        if hops > 50:
            raise SpecError("Reference cycle detected.")
        ref = node["$ref"]
        doc = _doc_of(node) or spec
        if not isinstance(doc, dict):
            raise SpecError(f"Reference could not be resolved: {ref}")
        resolver = getattr(doc, "_resolver", None)
        if ref.startswith("#"):
            if len(ref) == 1:
                node = _tagged(doc, doc)
            else:
                node = _tagged(_navigate(doc, ref[1:], ref), doc)
        elif resolver is not None:
            node = resolver.resolve(ref, doc)
        else:
            raise SpecError(f"Only local references are supported, got: {ref}")
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
