# Release SpecSentinel

Dieses Dokument beschreibt die exakten Schritte für ein Release (z. B. 0.4.0).
Die Veröffentlichung eines GitHub Release lädt **sofort und unwiderruflich** auf
PyPI hoch (`publish.yml`, Trusted Publishing via `id-token`). Nähert ihr euch dem
letzten Schritt, ist die Version damit öffentlich. Es gibt kein Zurück bei
PyPI-Namen oder -Versionen.

## Versionsstellen

Vor dem Release müssen alle folgenden Stellen dieselbe Version tragen
(Konsistenz wird durch `tests/test_version_consistency.py` in CI geprüft):

| Stelle | Beispiel |
| --- | --- |
| `pyproject.toml` → `version` | `version = "0.4.0"` |
| `src/specsentinel/__init__.py` → `__version__` | `__version__ = "0.4.0"` |

`action.yml` pinnt bewusst **keine** Version: Der `version`-Input hat einen
leeren `default`, dann installiert die Action die neueste PyPI-Version. Nur die
Beispielangabe in dessen Beschreibung wird angepasst (nicht durch den
Konsistenz-Test abgedeckt, im Release 0.3.0 manuell erledigt):

- `action.yml` → `version`-Input-Beschreibung (Beispiel `"0.3.0"`)
- `README.md` → Beispiele mit Versionsangaben und PyPI-Badge
- `.github/ISSUE_TEMPLATE/bug_report.yml` → Versions-Platzhalter
- `tests/test_version_consistency.py` selbst, falls seine Logik angepasst wird

Will die Action dagegen bei jedem Release exakt die neue Version installieren,
wird zusätzlich der `default` des `version`-Inputs auf `"0.4.0"` gesetzt; dann
greift automatisch der Konsistenz-Test, weil `action.yml` ein
`specsentinel==0.4.0` enthält und mit der Projektversion übereinstimmen muss.

## Schritte (z. B. für 0.4.0)

**Vorab auf einem Feature-Branch:**

1. Neue Features/Fixes auf `main` (oder einen Feature-Branch) committen,
   Tests und `mypy src/specsentinel` sind grün (CI prüft beides auf allen
   Python-Stufen 3.9–3.12).
2. `CHANGELOG.md`: Einträge unter `## [Unreleased]` sammeln. Keine eigenen
   Versionsabschnitte neben `[Unreleased]` anlegen.

**Release-Commit (auf main, als PR wie `Release 0.3.0 (#12)`):**

3. Alle Versionsstellen aus der Tabelle auf `0.4.0` anheben. Optional die
   `version`-Input-Beschreibung in `action.yml` aktualisieren.
4. `CHANGELOG.md`: Abschnitt `## [0.4.0] - YYYY-MM-DD` aus dem (jetzt leeren)
   `[Unreleased]`-Block benennen und Inhalt dorthin übertragen. Das Datum ist
   der geplante Veröffentlichungstag. `[Unreleased]` bleibt oben als leerer
   Platzhalter stehen.
5. Tests und `mypy` lokal laufen lassen (`pip install -e ".[dev]"` in frischer
   venv, dann `pytest -q` und `mypy src/specsentinel`).
6. PR stellen und auf grüne Checks warten. Merge nach `main`.

**Veröffentlichung:**

7. Auf GitHub einen Tag `v0.4.0` auf `main` setzen und ein **GitHub Release**
   veröffentlichen (Titel `0.4.0`, Notizen aus dem CHANGELOG-Abschnitt).
   Die Veröffentlichung des Releases triggert `publish.yml`
   (`on: release: types: [published]`), das das Paket baut und per
   Trusted Publishing auf PyPI veröffentlicht. **Achtung: ab hier ist die
   Version öffentlich und der Upload unumkehrbar.**
8. Im Release-Abschnitt `Workflow runs` die `publish`-Pipeline prüfen —
   beide Jobs (`build`, `publish`) müssen grün sein.

**Nachweis:**

9. In frischer venv: `pip install specsentinel && specsentinel --version` →
   zeigt die neue Version. Alternativ `pip index versions specsentinel`.
10. `action.yml`-Smoke-Test prüft in CI bereits das installierte Paket
    (`action_test.yml`); bei gepinnter Version (`version`-Input mit konkretem
    Wert) wird exakt diese Version installiert und abgefragt.

## Warum test_version_consistency.py existiert

Der Test vergleicht `pyproject.toml` und `src/specsentinel/__init__.py`
miteinander und prüft, dass jede in `action.yml` fest gepinnte Version zur
Projektversion passt (derzeit pinnt `action.yml` nichts, der Test greift also
erst, wenn jemand einen `default` setzt oder ein `specsentinel==X` einfügt).
Er läuft als Teil von `pytest` in `ci.yml` und schlägt fehl, sobald jemand die
Versionsstellen auseinanderlaufen lässt.