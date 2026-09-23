# Bestandsaufnahme SpecSentinel

Stand: 2026-09-23, Branch `pflege-2026-09-23`
(Stichproben-Pflege-Auftrag; dieser Bericht dokumentiert die Ausgangslage, keine Änderungen)

## a) Projektstruktur und Erkennung von Abweichungen

SpecSentinel 0.3.0 ist ein Python-Kommandozeilentool (≥ 3.9, einzige
Laufzeitabhängigkeit PyYAML) mit einer GitHub Action. Aufteilung:

- `src/specsentinel/cli.py` — Argumente, Fehlerpfad (Exit 2, ohne Traceback), JSON- und Textformat.
- `src/specsentinel/spec.py` — Laden einer OpenAPI-Datei oder URL (JSON oder YAML via `yaml.safe_load`), Übersetzen von Swagger-2.0-Dokumenten (Import aus `swagger2.py`), Auflösen von `$ref` innerhalb und über Dokumente hinweg (auch URLs), Iteration über GET-Operationen.
- `src/specsentinel/runner.py` — Parameterwerte aus Spec/Params-Datei/`--param` (später gewinnt), Aufbau und Senden der GET-Requests, `OperationResult`/`Report`, Include/Exclude-Filter (fnmatch) und `--delay`.
- `src/specsentinel/checker.py` — Vergleich einer live HTTP-Antwort mit der Operation: Statuscode (`UNDOCUMENTED_STATUS`), Content-Type, JSON-Parsing, Schema-Prüfung (Typen, Pflichtfelder, Enums, oneOf/anyOf, allOf, `additionalProperties`, Formate/Längen/Grenzen/Pattern, Header). `Finding(severity, code, location, message)`.
- `src/specsentinel/baseline.py` — `--write-baseline`/`--baseline`: Befunde werden über (Methode, Pfad, Code, Location) gematcht, nicht über den Text.
- `src/specsentinel/report.py` — Text- und JSON-Ausgabe.
- `tools/spec_smoke.py` — Smoke-Test gegen große öffentliche Specs (Petstore, GitHub, Stripe).
- `tests/` — 13 Testdateien und `conftest.py` (Demo-Server-Fixtures).
- `.github/workflows/` — `ci.yml` (Tests auf 3.9–3.12 bei push/PR), `action_test.yml` (Smoke-Test der Action), `publish.yml` (PyPI bei Release).

Ablauf der Drift-Erkennung: CLI lädt die Spec, der Runner iteriert alle
GET-Operationen aus der Spec, ruft sie gegen `--url` auf und vergleicht die
Antwort mit der jeweiligen Operation. 15 Finding-Codes (siehe README), davon neun
Fehler und sechs Warnungen; `--strict` stuft auch Warnungen als Drift ein.
Exit: 0 = MATCH, 1 = DRIFT, 2 = unvollständig.

**Grenze im Modell:** Es werden nur Operationen geprüft, die *in der Spec
vorkommen*. Eine Antwort, die ein Endpunkt liefert, den die Spec gar nicht kennt,
kann nicht erkannt werden (kein Endpunkt-Scan der live API).

## b) Testlauf

Lokal auf dem Stand von Branch `pflege-2026-09-23` (vor jeglichen Änderungen):

```
.venv/bin/python -m pytest -q
136 passed in 28.02s
```

Aufteilung (Tests pro Datei):

| Datei | Tests |
|---|---|
| tests/test_checker.py | 25 |
| tests/test_swagger2.py | 20 |
| tests/test_format_warnings.py | 18 |
| tests/test_external_refs.py | 15 |
| tests/test_e2e.py | 12 |
| tests/test_baseline.py | 12 |
| tests/test_errors.py | 11 |
| tests/test_filters.py | 8 |
| tests/test_response_headers.py | 8 |
| tests/test_json_output.py | 3 |
| tests/test_smoke.py | 2 |
| tests/test_delay.py | 2 |
| **Gesamt** | **136** |

Abdeckungs-Messung: es ist kein Coverage-Werkzeug installiert
(`pytest-cov` ist nicht in `pyproject.toml`), daher keine Prozentangabe.
Eine Messung wäre erst nach Installation eines neuen Werkzeugs möglich.

## c) Unterstützte OpenAPI-Versionen und Lücken

- **Swagger 2.0**: wird erkannt (`swagger: 2.0`) und in ein internes
  OpenAPI-3-Dokument übersetzt (`swagger2.py`). Nicht übersetzbar – Pfade mit
  `type: file`-Parametern, Body-Parametern, `$ref`-Parametern – werden als
  „SKIPPED" gemeldet statt abzubrechen. Andere Swagger-Versionen werden
  abgelehnt (`Swagger version X` → Exit 2).
- **OpenAPI 3.x**: wird akzeptiert, sobald ein Feld `openapi` vorhanden ist.
  **Der Versionswert selbst wird nicht geprüft** – auch `openapi: 99.0` würde
  durchgehen. Geprüft werden Pfade, Parameter, Responses, Schemas, `$ref`
  (auch über Dateien und URLs), `nullable`, `enum`, `format`,
  `min/maxLength`, `minimum/maximum`, `pattern`, `oneOf/anyOf`, `allOf`,
  `additionalProperties`, Pflicht-Header.
- **OpenAPI 3.1**: wird akzeptiert (obiges Feld reicht), aber 3.1-typische
  Formen sind nicht vollständig gelöst:
  - `exclusiveMinimum`/`exclusiveMaximum` (in 3.1 Zahlen) werden ignoriert,
    in 3.0 sind sie boolesche Modifikatoren, die ebenfalls ignoriert werden.
  - `const` (3.1) wird nicht geprüft.
  - `type: ["string", "null"]` wird verstanden (Null erlaubt), ebenso
    `$ref` nach `#/$defs/...` (generisches Navigieren).
  - `readOnly`/`writeOnly`, `contentMediaType`, `$schema` pro Schema: ignoriert.
  - Webhooks/`pathItems` auf Dokumentebene (3.1): ignoriert, da nur `paths`
    bzw. GET iteriert werden.

## d) PyPI-Version vs. Repo-Stand

- `pyproject.toml` und `__init__.py`: **0.3.0** (Repo-Stand, main).
- PyPI (per `pip index versions specsentinel`): **neueste veröffentlichte
  Version ist 0.2.0** (0.1.0 bis 0.2.0 vorhanden). Im lokalen `.venv` ist 0.1.0
  installiert.
- Git-Tags: `v0.1.0`, `v0.1.1`, `v0.1.2`, `v0.2.0` – **kein `v0.3.0`-Tag**.
- CHANGELOG enthält bereits einen `[0.3.0]`-Eintrag (2026-09-21) und das
  README verweist auf `@v0.3.0` in der Action-Beispielnutzung.

**Befund:** Das Repo liegt eine Version vor der tatsächlich publizierten.
0.3.0 (Baseline, klare Fehlerpfade) ist weder getaggt noch auf PyPI, das
README/Action-Beispiel mit `@v0.3.0` würde aktuell auf einen nicht
existierenden Tag zeigen. Das Auspublizieren ist laut Auftrag nicht Teil
dieser Pflege.

## e) Katalog gefundener Schwachstellen

Sicherheit:

1. **`$ref` liest lokale Dateien und beliebige URLs** (gewollt, in README/
   SECURITY dokumentiert, 0.1.2): eine vertrauliche Spec kann Dateien vom
   Rechner lesen oder Fremd-URLs abrufen (SSRF-artig). Es gibt keine
   Allowlist, keinen Größen-Limit und keinen Folgeschutz für die geladenen
   Dokumente. Nur vertrauenswürdige Specs verwenden – die Doku sagt das,
   ein technischer Schutz fehlt.
2. **YAML wird überall mit `yaml.safe_load` geladen** (`spec.py`, `cli.py`):
   kein `yaml.load`. Hier besteht kein Handlungsbedarf, dies ist der
   erwünschte Zustand.
3. **Kein Size-Limit beim Herunterladen** von Specs/Referenzdokumenten
   (`urllib.request.urlopen`, Timeout 20 s fest). Eine böswillige oder
   defekte Spec kann beliebig viel Speicher binden.
4. **Downloads folgen Weiterleitungen**, ohne Grenze/Prüfung.

Untersetzung / Wartbarkeit:

5. **Fehlende Pfadangabe in Fehlermeldungen:** `Finding.location` bezeichnet
   den Ort in der *Antwort* (`body.name`), nicht den Ort in der *Spec*. Ein
   Befund sagt z. B. „status 503 is not documented (documented: 200)", nennt
   aber nicht `paths./x.get.responses`, wo das dokumentiert sein müsste.
6. **Fehlende Typannotationen** (kein mypy/pyright installiert, aber der Code
   kennt `from __future__ import annotations`):
   u. a. `checker.type_of(value)`, `checker.enum_contains(options, value)`,
   `checker._validate_constraints(schema, value, path)`,
   `checker.match_response(...)`, `checker.pick_media_type(...)`,
   `checker.check_response(...)`, `runner._example_value(spec, param)`,
   `runner._as_text(value)`, `runner.build_request(...)`,
   `spec._tagged(value, doc)`, `spec._doc_of(node)`,
   `spec._navigate(...)`, `spec.deref(...)`, `spec.resolve_ref(...)`,
   `spec.iter_get_operations(...)`, `swagger2.rewrite_refs(value)`,
   `cli._one_line(text)`.
7. **Toter Code:** `spec.resolve_ref` ist definiert und öffentlich, wird aber
   von keiner anderen Stelle verwendet (nur die interne Navigation `_navigate`
   in `deref` ist im Einsatz).
8. **`openapi`-Versionswert wird nicht validiert** (siehe c).
9. **Warnungen ohne Folgeprobe:** `exclusiveMinimum`/`exclusiveMaximum`/
   `const` werden still ignoriert, ohne dass das jemand erfährt (siehe c) —
   eine Spec kann so schwächer geprüft werden, als sie vorgibt.

Testlücken (korreliert mit Auftrag TEIL 2a):

10. „Endpunkt entfernt": ein in der Spec dokumentierter Endpunkt, den die live
    API nicht mehr liefert (404 o. ä.), wird generisch als `UNDOCUMENTED_STATUS`
    gemeldet (`test_checker.py` deckt den Code ab), aber es gibt keinen Tests,
    der den Fall „dokumentierter Endpunkt antwortet 404 → DRIFT" explizit
    abbildet.
11. „Endpunkt neu": ein Endpunkt in der live API, der nicht in der Spec steht,
    ist mit dem aktuellen Modell gar nicht erkennbar (kein Test möglich,
    Modellgrenze, siehe a).
12. „Parameter geändert": Header-Anforderungen werden geprüft
    (`MISSING_RESPONSE_HEADER`), unbelegte Pfad-/Query-Parameter führen zu
    SKIP. Einen expliziten Tests für „Parameter fehlt in der Spec von
    auth-Header/query" gibt es nicht als Drift-Typ.

CI:

13. **CI deckt Tests, aber keinen Typscheck:** `ci.yml` fährt `pytest`
    auf Python 3.9–3.12 bei jedem push/PR (grün). Ein Typscheck läuft
    nirgends (kein Werkzeug installiert). `action_test.yml` deckt die
    Action-Smoke-Szenarien ab, `publish.yml` nur bei Release.