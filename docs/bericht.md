# Abschlussbericht

Pflege-Auftrag SpecSentinel, 2026-09-23, Branch `pflege-2026-09-23`
(von `main` = `3d48afc`). Kein Push, kein Merge, kein Release.

## Commits auf diesem Branch

| Commit | Inhalt |
|---|---|
| `ef67147` | TEIL 1: `docs/bestand.md` – Bestandsaufnahme |
| `6217133` | TEIL 2a: Drift-Typ-Tests `tests/test_e2e.py` |
| `46414ab` | TEIL 2b: Size-Limit für Downloads `src/specsentinel/spec.py` + `tests/test_external_refs.py` |
| `1064724` | TEIL 2c: Typannotationen in `baseline.py`, `checker.py`, `cli.py`, `report.py`, `runner.py`, `spec.py`, `swagger2.py` |
| `f4e3e19` | TEIL 2d: Spec-Pfad in Finding-Meldungen `checker.py`, `runner.py` + `tests/test_checker.py` |
| `c51cc74` | TEIL 3: `docs/fahrplan.md` – Roadmap und Sichtbarkeit |

Insgesamt 12 Dateien geändert: 3 neue (`docs/bestand.md`, `docs/fahrplan.md`),
9 angepasste (siehe `git diff --stat main...HEAD`).

## Geänderte Dateien

- `docs/bestand.md` (neu), `docs/fahrplan.md` (neu)
- `src/specsentinel/baseline.py`, `checker.py`, `cli.py`, `report.py`,
  `runner.py`, `spec.py`, `swagger2.py`
- `tests/test_checker.py`, `tests/test_e2e.py`, `tests/test_external_refs.py`

Dokumentation am Repo-Stand: README, CHANGELOG, aktuelle Version wurden
absichtlich **nicht** verändert (kein Release im Auftrag). Das README verweist
weiterhin auf `@v0.3.0`, obwohl der Tag fehlt — siehe „unklar" unten.

## Testergebnis

Vorher (Stand `main`, ohne Auf-Ansätze): **136 passed in 28.02 s**.
Nachher: **140 passed in 29.08 s**.

Hinzu kamen zwei neue Drift-Tests in `test_e2e.py` (Endpunkt-entfernt,
Spec-getriebene Grenze Endpunkt-neu), ein Size-Limit-Test in
`test_external_refs.py` und ein Spec-Pfad-Test in `test_checker.py`.
Alle Läufe grün vor jedem Commit.

## Behobene Sicherheitsbefunde (bestand 1e)

1. **Unbegrenztes Herunterladen von Specs/Referenzen** behoben
   (`spec.py: MAX_DOWNLOAD_BYTES = 50 MB`, `_read_limited`): Ein entfernter
   Server kann seither nicht mehr beliebig viel Speicher binden. Befund 1e/3.
2. YAML wird weiterhin überall mit `yaml.safe_load` geladen (Befund 1e/2 war
   bereits in Ordnung, keine Änderung).
3. Die übrigen Security-Befunde 1e/4 (Redirects ohne Grenze), der bewusste
   `$ref`-Zugriff auf Dateien/URLs (dokumentiertes Feature) und fehlende
   Allowlist sind **bewusst nicht** geändert: Eine Allowlist wäre ein
   Verhaltensbruch, Redirects ein Kompatibilitätsrisiko; beide stehen als
   Optionen im Fahrplan (#5).

## Verhaltensänderungen mit Test und Berichtseintrag

- **TEIL 2d (f4e3e19):** Finding-Meldungen für Response-Ebene tragen jetzt
  einen Verweis auf die Spec-Stelle, z. B.
  `status 503 is not documented (documented: 200) (in paths./x.get.responses)`.
  Die Meldungstexte ändern sich; Location/Severity/Code bleiben stabil, und
  Baselines matchen ohnehin über (Methode, Pfad, Code, Location) und nie über
  den Text. Belegt durch `test_undocumented_status_points_at_the_spec_response`.
- **TEIL 2a (6217133):** Tests dafür, dass ein dokumentierter Endpunkt, der
  mit 404 antwortet, als `UNDOCUMENTED_STATUS` DRIFT ist (exit 1), und dass ein
  Endpunkt, den die live API zusätzlich liefert, das Ergebnis nicht verändert
  (Spec-getriebenes Modell).
- **TEIL 2b (46414ab):** Downloads über 50 MB schlagen fehl statt Speicher zu
  belegen. Belegt durch `test_download_over_size_limit_is_rejected`.

## Folgeauftrag (TEIL A–C), 2026-09-23

Fortsetzung auf demselben Branch `pflege-2026-09-23`. Weiterhin kein Push,
kein Merge, kein Release, kein `git add .`/`-A`, explizites Staging.

### TEIL A: Typscheck (mypy)

- `599c5aa` `chore(typing): mypy strikt als Dev-Dependency (dev extras + tool.mypy) (TEIL Aa)`:
  `mypy>=1` und `types-PyYAML` als Dev-Extras, `[tool.mypy]` mit
  `python_version = "3.9"` und `strict = true`, `files = ["src/specsentinel"]`.
  Die vom Auftraggeber freigegebene Antwort auf die Fahrplan-Frage #7
  („Darf mypy als Dev-Dependencies ergänzt werden?") war **ja**.
- `f0d25a0` `chore(typing): mypy-Fehler beheben und typecheck in CI (TEIL Ab/Ac)`:
  mypy-Fehler in `baseline.py`, `checker.py`, `cli.py`, `report.py`, `runner.py`,
  `spec.py`, `swagger2.py` behoben (v. a. Explicite `dict[str, Any]`-Parameter
  und Klassenvariablen-Annotationen). `ci.yml` prüft seither zusätzlich
  `mypy src/specsentinel` je Python-Version. Ergebnis: **Success: no issues
  found in 9 source files**.

### TEIL B: Fahrplan 1–5

| Nr. | Commit | Inhalt |
|---|---|---|
| 1 | `bea4573` | `openapi`-Version prüfen (nur `3.x` akzeptiert) und im JSON-Output als `openapi_version` anzeigen (Swagger-Quellen: `swagger 2.0`). Neue `tests/test_openapi_version.py`, Ergänzung in `test_swagger2.py` |
| 2 | `064c4d6` | `const` (→ `CONST_MISMATCH`) und `exclusiveMinimum`/`exclusiveMaximum` prüfen: 3.1-Zahlen direkt, 3.0 als Bool-Modifier auf `minimum`/`maximum` (→ `RANGE_MISMATCH`). 8 neue Tests in `test_format_warnings.py` |
| 3 | – | **Übersprungen** (siehe unten) |
| 4 | `298bb3f` | Format-Checks `date` (RFC 3339 full-date) und `byte` (Base64) → `FORMAT_MISMATCH`; `test_unknown_format_is_ignored` auf das weiterhin unbekannte Format `password` umgestellt |
| 5 | `6c79249` | CLI-Optionen `--spec-max-bytes` (Default 50 MiB) und `--spec-timeout` (Default 20 s) für Download von Spec und Referenzen; 3 neue Tests in `test_external_refs.py` |

**Fahrplan 3 (Endpunkt-Scan) — bewusst übersprungen.** Die Erkennung von
Endpunkten, die die live API zusätzlich zu der Spec liefert, widerspricht dem
Spec-getriebenen Modell von SpecSentinel (es ruft nur GET-Operationen aus der
Spec auf) und würde den Output/Exit-Code-Semantik erweitern — laut Fahrplan 3
und `bestand.md` d ist das ein neues Feature, dessen Erkennung einen
Verhaltensbruch bedeutet (STOPPGRUND, siehe „Nicht getan"). Die Grenze ist
bereits durch `test_e2e.py` als erwartetes Verhalten dokumentiert. Ein
Anschluss-Auftrag kann den Scan als opt-in (`--scan-extra-paths`) auf der Basis
von Fahrplan 3 aufnehmen.

- `99e8e28` `docs: CHANGELOG-Einträge für Fahrplan 1, 2, 4 und 5 (0.3.0 unveröffentlicht)`:
  Neue Sektion `## 0.3.0 (unveröffentlicht)` in `CHANGELOG.md` mit den
  anwendersichtbaren Änderungen aus Fahrplan 1, 2, 4, 5.

### TEIL C: Paketbau

- Wheel und sdist gebaut (`python -m build`): `specsentinel-0.3.0-py3-none-any.whl`
  und `specsentinel-0.3.0.tar.gz`.
- Beide in einer frischen venv (Python 3.9.6) installiert; `specsentinel --version`
  liefert `0.3.0`. Ein Lauf gegen `examples/demo_server.py` mit
  `examples/petstore.yaml` erkennt den gewollten Drift (exit 1) und meldet
  `"openapi_version": "3.0.3"` — das Paket ist selbst konsistent mit dem Stand.
- Kein Upload an Test-PyPI/PyPI, kein Tag, kein verschieben nach `dist/`.
  Soll veröffentlicht werden, ist das ein eigener Auftrag (vgl. Fahrplan #10).

### Testergebnis (Endstand)

**158 passed**, mypy: **Success: no issues found in 9 source files**. Grüne
Läufe vor jedem Commit.

## Nachtrag „Ausbau" (TEIL D–G), 2026-09-24

Neuer Branch `ausbau-2026-09-24` (von `pflege-2026-09-23` = `de258ec`).
Weiterhin kein Push, kein Merge nach `main`, kein Release, keine
Versionsänderung.

### TEIL D: `origin/main` in den Branch mergen

- **Ergebnis:** Merge-Commit `a2cc021`, Code war konfliktfrei
  (`git diff --name-status pflege-2026-09-23 origin/main` zeigte vorab, dass
  nur `CHANGELOG.md` divergierte). Einziger Konflikt inhaltlicher Art:
  `CHANGELOG.md`.
- **Aufgelöster Konflikt:** `pflege-2026-09-23` trug einen eigenen Abschnitt
  `## 0.3.0 (unveröffentlicht)` (Fahrplan-Einträge), `main` hat dieselben
  Inhalte bereits in `## [0.3.0] - 2026-09-24` veröffentlicht. Lösung wie
  vorgegeben: pflege-Abschnitt verworfen, `[0.3.0]`-Abschnitt von `main`
  unverändert, oben steht der leere `## [Unreleased]`. `CHANGELOG.md` ist damit
  byte-identisch mit `origin/main`.
- Der automatische Ort-Merge (`e53ac04`) wurde verworfen und nach Auflösung neu
  als echter Zwei-Eltern-Merge erstellt, damit `origin/main` Ancestor bleibt.
- **Reihenfolge eingehalten:** erst volle Tests + mypy grün (158 passed,
  mypy Success), danach der Merge-Commit.

### TEIL E: CI nachschärfen

- `ci.yml`: `mypy src/specsentinel` ist jetzt ein eigener benannter Schritt
  (`Type check (mypy)`); `pytest` ebenso (`Tests`).
- Actions auf Node-24-Versionen angehoben (die alten zielten auf Node 20):
  - `actions/checkout@v4` → **`@v5`** (Node 24, Runner ≥ 2.327.1) in
    `ci.yml`, `action_test.yml`, `publish.yml`
  - `actions/setup-python@v5` → **`@v6`** (Node 24, v6.0.0) in `ci.yml`,
    `publish.yml` und `action.yml`
  - `actions/upload-artifact@v4` → **`@v6`** (v6 ist die erste Node-24-Version;
    v5 lief noch auf Node 20) in `publish.yml`
  - `actions/download-artifact@v4` → **`@v7`** (erste Node-24-Version; v5/v6
    liefen noch auf Node 20) in `publish.yml`
  - `publish.yml`: ausschließlich Versionsnummern geändert.
- `ubuntu-latest` migriert laut GitHub (Changelog 2026-09-17, Issue #14748)
  zwischen **19.10. und 19.11.2026** von Ubuntu 24.04 auf **26.04**. Für
  SpecSentinel ist das Risiko gering: CI installiert Python über
  `setup-python@v6`, Tests + mypy laufen in einer frischen venv aus
  `.[dev]`; es gibt keine Abhängigkeit von vorinstallierten Systempaketen.
  **Empfehlung:** `ubuntu-latest` beibehalten, die Migration beobachten; nur
  festpinnen (`ubuntu-24.04`), falls ein Lauf Ende Oktober 2026 unerwartet
  bricht. Kein aktueller Grund zum Pinnen.

### TEIL F

**a) `action.yml` – welche SpecSentinel-Version wird installiert?**

- `action.yml` pinnt **keine** Version: Der Input `version` hat den leeren
  Default, ohne Wert wird `pip install specsentinel` = neueste PyPI-Version
  genutzt. Damit gibt es **keine feste Nummer, die bei 0.3.0 veraltet wäre**.
  Die Beispielangabe in der `version`-Beschreibung lautet bereits „0.3.0"
  (seit Release `54f25c8`). **Kein Handlungsbedarf, keine Änderung.**
- Einziger Randfund: `action_test.yml` pinnt in einem Testfall bewusst
  `version: "0.1.1"` (Absicht: Pinning-Verhalten testen, berücksichtigt die
  aktuelle Version nicht). Bewusst unverändert — er verifiziert den
  Pinning-Pfad, nicht die Default-Version.
- Konsistenz mit der Projekt-Versionspflicht wird durch
  `tests/test_version_consistency.py` sichergestellt (s. u.).

**b) Versionskonsistenz-Test** — `tests/test_version_consistency.py` (neu):
- `pyproject.toml`-`version` == `src/specsentinel/__init__.py`-`__version__`
  (zwingend).
- Jede in `action.yml` vorkommende Fest-Pin (`specsentinel==X`) muss zur
  Projektversion passen (greift, sobald jemand einen Default setzt);
  aktuell kein Pin → Test grün.
- Läuft als Teil von `pytest` in `ci.yml`, schlägt also in CI fehl; von Hand
  verifiziert, dass er bei Version-0.3.0/„9.9.9"-Abweichung rot wird.

**c) `docs/release.md`** (neu): exakte Release-Schritte — Versionsstellen
(`pyproject.toml`, `__init__.py`), optionale `action.yml`-Pin, CHANGELOG-Umbau
von `[Unreleased]` zu `[0.x.0]`, PR/Merge, GitHub-Release + Tag `v0.x.0`,
publish-Pipeline. **Warnhinweis:** Die Veröffentlichung des GitHub Release
lädt sofort und unumkehrbar auf PyPI hoch (`publish.yml`, Trusted Publishing).

### Testergebnis (Endstand Nachtrag)

**160 passed**, mypy: **Success: no issues found in 9 source files**. (158 vor,
+2 Versionskonsistenz-Tests.)

### Drei Stellen, zuerst zu lesen

1. `docs/bericht.md` (dieser Abschnitt „Nachtrag Ausbau") – Kontext des Branches.
2. `docs/release.md` – Release-Ablauf mit dem PyPI-Soforthochladen-Hinweis.
3. `tests/test_version_consistency.py` – die neue Versionskonsistenz-Sicherung
   samt zugehörigem CI-Effekt.

## „Unklar" / offene Punkte

- **OpenAPI-Version:** `spec.py` prüft nur das Vorhandensein von `openapi`,
  nicht dessen Wert. Ob 3.1-Dokumente geprüft werden *sollen* und welche
  3.1-Eigenheiten dafür nötig sind, war aus dem Repo allein nicht eindeutig –
  der Auftrag nennt keine Zielversion. Der Status (akzeptiert, aber
  `const`/numerische `exclusiveMinimum`/`Maximum` ungeprüft) ist in
  `bestand.md` c festgehalten; Fix als Fahrplan #2.
- **PyPI vs. Repo:** PyPI führt 0.2.0, das Repo 0.3.0 (`pyproject.toml`,
  CHANGELOG), Tag `v0.3.0` fehlt, README verweist auf `@v0.3.0`. Ein Release
  ist laut Auftrag ausgeschlossen; deshalb blieb es bei der Dokumentation
  (`bestand.md` d, Fahrplan #10). **Frage an den Auftraggeber:** Soll 0.3.0
  gepublisht/getaggt werden?
- **Typscheck:** Kein Typprüf-Werkzeug (mypy/pyright) ist installiert; `ci.yml`
  läuft nur `pytest`. Einen Typscheck einzurichten hieße eine neue
  Dev-Abhängigkeit — STOPPGRUND laut Auftrag (`bestand.md` e/13, Fahrplan #7).
  **Frage:** Darf mypy als Dev-Dependenz ergänzt werden?
- **Coverage:** Kein Coverage-Werkzeug vorhanden, daher keine Prozentzahl
  (`bestand.md` b, Fahrplan #6).
- **Endpunkt-neu-Erkennung:** Im aktuellen Modell nicht möglich (Spec-getrieben,
  nur GET aus der Spec). Test dokumentiert die Grenze; eine Erkennung wäre ein
  neues Feature (Fahrplan #3), das den Output erweitern würde.

## Nicht getan (bewusst)

- Kein Push, kein Merge, kein Tag, kein PyPI-Release, keine Versionsänderung.
- Kein `git add .`/`-A`, nur explizites Staging.
- Die ungemergten `ausbau4`-Arbeiten (JUnit-Output, Step-Summary, Action-Output)
  blieben unberührt.
- Keine neuen Laufzeit-Abhängigkeiten. `mypy` und `types-PyYAML` kamen im
  Folgeauftrag TEIL A als Dev-Dependencies hinzu (vom Auftraggeber freigegeben,
  Fahrplan #7).
- Öffentliche Schnittstellen (CLI, Python-API, Ausgabeformat) unverändert;
  alle Änderungen erweitern nur Meldungstexte und betten neue optionale
  Parameter ein.

## Empfohlene nächste Schritte (Details: docs/fahrplan.md)

1. `openapi`-Version prüfen und sichtbar machen; 2. `const`/numerische
   Exclusive-Grenzen; 3. Endpunkt-Scan für in der Spec fehlende Endpunkte;
   4. Formate `date`/`byte`; 5. konfigurierbare Download-Grenzen;
   6. Coverage in CI; 7. mypy in CI; 8. einheitliche Fehlertexte;
   9. GitHub-Action-Annotations; 10. Release-Kette vollenden.
## Ausbau 2026-09-25

Branch `ausbau-2026-09-25` (von `main` @ `a7b5861`). Kein Release, keine
Versionsänderung (bleibt 0.3.0), alle CHANGELOG-Einträge unter
`## [Unreleased]`. Nicht gepusht.

### Commits je Teil

| Teil | Commit | Inhalt |
|---|---|---|
| A Python-Versionen | `0936cfc` | CI-Matrix um 3.13 und 3.14, Klassifizierer `3 :: Only` |
| B Fahrplan 8 | `f292a33` | Fehlermeldungen Params- und Baseline-Datei mit Datei und `(in ...)`-Stelle; unlesbare Datei → Exit 2 statt Traceback |
| B Fahrplan 9 | `e4e67a3`, `f4365ad` | GitHub Action: Job-Summary und Annotation je Drift (`action/summary.py`, Eingabe `summary`); Folgecommit: Namenskonflikt mit `from __future__ import annotations` behoben (bei `mypy --strict` erst nach dem ersten Commit bemerkt) |
| C b Beispiele | `e4de538` | `examples/01_simple_run.sh`, `02_baseline.sh`, `03_swagger2.sh`, `examples/README.md`, Test `tests/test_examples.py` |
| C a README | `d58b0ba` | Erste zehn Zeilen: was, für wen, Auszug eines echten Laufs; veralteter „Real output"-Block durch echte 0.3.0-Ausgabe ersetzt; Test `tests/test_readme_example.py` |
| C c Action-Doku | `8079f0c` | `docs/github-action.md` (Pinning, Baseline, include/exclude), im README verlinkt; Test `tests/test_github_action_doc.py` |
| C d Metadaten | `90a942a` | `project.urls` (Documentation, Source), Keywords, zwei Klassifizierer; mit `python -m build` und `twine check` geprüft |
| E Bericht | (dieser Commit) | dieser Abschnitt |

### Fahrplan 6 bis 10

| Nr. | Status | Begründung |
|---|---|---|
| 6 Coverage + Gate | übersprungen | Weder `coverage` noch `pytest-cov` sind Dev-Abhängigkeit; Teil D c schreibt für diesen Fall „nur vorschlagen" vor (Vorschlag unten). |
| 7 mypy in CI | bereits erledigt | Steht seit `a7b5861` in `.github/workflows/ci.yml` (Schritt „Type check (mypy)"). |
| 8 Fehlermeldungen | umgesetzt | `f292a33`, 9 Tests in `tests/test_file_errors.py`. Exit-Codes und JSON-Format unverändert, nur Meldungstexte. |
| 9 Action Summary/Annotations | umgesetzt | `e4e67a3`/`f4365ad`, 8 Tests in `tests/test_action_summary.py`; zusätzlich lokal mit bash (`-eo pipefail`, wie GitHub) gegen die Demo-API ausgeführt: Exit 1 bzw. 0 durchgereicht, Summary und Annotationen korrekt. Wirkt erst ab dem nächsten Action-Tag. |
| 10 Release-Kette | ausgelassen | Auftrag: kein Release. Außerdem inzwischen überholt: Tag `v0.3.0` existiert, PyPI steht auf 0.3.0 (`docs/fahrplan.md` ist in diesem Punkt veraltet, nicht geändert). |

### Python-Versionen: CI 3.13/3.14 noch nicht gesehen

Die CI-Matrix enthält jetzt 3.9 bis 3.14. **Die Läufe für 3.13 und 3.14 habe
ich nicht gesehen**: Der Branch ist nicht gepusht, lokal gibt es nur
Python 3.9.6, und Docker/Colima habe ich nicht ungefragt gestartet. Eine
statische Suche nach in 3.13/3.14 entfernten Standardbibliotheks-Modulen
(`cgi`, `imghdr`, `telnetlib`, `distutils`, `pkg_resources` u. a.) fand
nichts; PyYAML 6.0.3 hat Wheels für beide Versionen. **Die Klassifizierer für
3.13 und 3.14 fehlen deshalb bewusst**; sie gehören erst nach einem grünen
CI-Lauf hinein (Einzeiler in `pyproject.toml` plus CHANGELOG).

### Vorschlag Mindestversion (`requires-python` nicht geändert)

- Python 3.9 bekommt seit Oktober 2025 keine Sicherheitsupdates mehr; 3.10
  endet im Oktober 2026, also in wenigen Tagen.
- Vorschlag: mit dem nächsten Minor-Release (0.4.0) `requires-python >=3.10`,
  im CHANGELOG als Breaking Change für 3.9-Nutzer angekündigt; 3.9 aus
  Matrix und Klassifizierern nehmen. Anfang 2027 dann `>=3.11`.
- Warum nicht sofort 3.11: Ubuntu 22.04 LTS (Support bis 2027) bringt 3.10 als
  System-Python mit; wer SpecSentinel dort ohne `setup-python` nutzt, würde
  sonst ausgesperrt. In GitHub Actions ist die Version egal (`setup-python`).
- Folge fürs Repo: Die lokale Entwicklungsumgebung `.venv` läuft auf dem
  macOS-System-Python 3.9 und müsste neu angelegt werden.

### Teil D: Pflege

**a) Pinning in `action_test.yml` (0.1.1 → 0.3.0?), nicht geändert.**
0.3.0 ist auf PyPI verfügbar (geprüft: Releases 0.1.0 bis 0.3.0). Empfehlung:
0.1.1 **nicht ersetzen, sondern einen zweiten Schritt mit 0.3.0 ergänzen.**
Der Test prüft den Pinning-Mechanismus, nicht Funktionen; 0.1.1 belegt
zusätzlich, dass die Action mit der ältesten pinnbaren Version funktioniert.
Das ist seit Fahrplan 9 relevanter, weil `action/summary.py` den Textbericht
aller Versionen lesen muss. Der Schritt mit 0.3.0 belegt die aktuelle Version.
Nur ersetzen, falls 0.1.1 auf dem Runner-Python einmal nicht mehr installierbar ist.

**b) TODO/FIXME.** Keine. Gesucht (auch ohne Groß-/Kleinschreibung, inkl.
`XXX`, `HACK`) in `src`, `tests`, `tools`, `docs`, `examples`, Workflows.
Einziger Marker: `# type: ignore[misc]` in `action/summary.py:30` (von mir, nötig,
`mypy --strict` meldet unbenutzte Ignores).

**c) Testabdeckung.** Nicht gemessen: kein Abdeckungswerkzeug in den
Dev-Abhängigkeiten. Vorschlag: `pytest-cov` in `[project.optional-dependencies] dev`,
CI-Schritt `pytest --cov=specsentinel --cov-report=term-missing` zunächst
ohne Schwelle, nach zwei Läufen Gate knapp unter dem gemessenen Wert (= Fahrplan 6).

### Endstand

- Tests: 160 → **189 passed** (Python 3.9.6, `.venv`).
- mypy: `mypy src/specsentinel` ohne Befund (9 Dateien); zusätzlich
  `mypy --strict action/summary.py` ohne Befund.
- CLI-Verhalten und JSON-Format unverändert; keine neue Laufzeitabhängigkeit;
  `requires-python` und Version unverändert.

### Offene Fragen

1. Soll die Action Eingaben für `--baseline`, `--include`, `--exclude`
   bekommen? Dann bräuchte `docs/github-action.md` den CLI-Umweg nicht mehr.
   Das ist eine sichtbare Schnittstelle und wirkt erst mit einem neuen Tag.
2. Action-Release: Die `summary`-Eingabe wirkt erst mit einem neuen
   Action-Tag. Wann und unter welcher Nummer?
3. Relative Links im README (`LICENSE`, `examples/README.md`,
   `docs/github-action.md`) funktionieren auf GitHub, aber nicht auf der
   PyPI-Seite. Beim nächsten Release auf absolute URLs umstellen?
4. `docs/fahrplan.md` ist teils veraltet (Tag `v0.3.0` und PyPI 0.3.0
   existieren inzwischen). Aktualisieren?
5. Klassifizierer 3.13/3.14 nach grünem CI-Lauf ergänzen (siehe oben).

### Drei Stellen, zuerst zu lesen

1. `action.yml` (Schritt „Check API against spec") und `action/summary.py`:
   die einzige Änderung, die in den Pipelines der Nutzer läuft (Exit-Code-
   Durchreichung über `PIPESTATUS`, `stop-commands`).
2. `src/specsentinel/baseline.py` (`load_baseline`) und
   `src/specsentinel/cli.py` (`_load_params_file`): geänderte Fehlertexte und
   der vorher ungefangene Lesefehler.
3. `docs/github-action.md`: öffentliche Doku mit Versprechen; bewusst ohne
   Eingaben, die es im `v0.3.0`-Tag nicht gibt (gegen den Tag geprüft).
