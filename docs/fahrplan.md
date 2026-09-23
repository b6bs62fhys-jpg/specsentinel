# Fahrplan SpecSentinel

Der Plan ist sortiert nach Nutzen/Aufwand (bestes Verhältnis zuerst). Es sind
reine Vorschläge für die Zukunft; bei jedem Punkt steht der Nutzen, der
geschätzte Aufwand und warum er an dieser Stelle sitzt. Die ersten fünf Punkte
beheben in der Reihenfolge die größten Lücken aus `bestand.md`.

## Die zehn wertvollsten nächsten Verbesserungen

### 1. `openapi`-Versionsfeld prüfen und Version sichtbar machen

- Nutzen: Heute wird jede Version akzeptiert, auch `openapi: 99.0`
  (`bestand.md` c/8). 3.1-Dokumente laufen unter voller 3.0-Palette, ohne dass
  jemand merkt, dass 3.1-Eigenheiten (`const`, numerische
  `exclusiveMinimum`/`Maximum`) wegfallen. Eine Abfrage mit klarer Meldung im
  JSON-Output (z. B. `"openapi_version": "3.1.0"`) macht den Prüfumfang ehrlich.
- Aufwand: gering (Erkennung in `spec.load_spec`, zwei Felder, ein Test).
- Warum zuerst: schließt die billigste Sicherheits- und Korrektheitslücke, kostet
  fast nichts.

### 2. `const` und numerische `exclusiveMinimum`/`exclusiveMaximum` prüfen (3.1)

- Nutzen: die auffälligsten 3.1-Lücken aus `bestand.md` c/9. `const` ist ein
  reiner Gleichheitstest, `exclusiveMinimum`/`Maximum` sind nur
  `<`/`>`-Varianten der bereits vorhandenen Bereichsprüfung.
- Aufwand: klein bis mittel (`_validate_constraints` in `checker.py`, 3–4 Tests).
- Warum: reine Erweiterung der Wertprüfung, keine Interface-Änderung, nutzt den
  schon vorhandenen Warnings-Pfad.

### 3. Endpunkt-Scan: „Endpunkt existiert in der API, fehlt in der Spec"

- Nutzen: die einzige echte Modellgrenze (`bestand.md` a und 2a/11). Heute
  kann SpecSentinel nicht erkennen, dass die API einen Endpunkt liefert, den
  die Spec nicht kennt — genau der Fall, den ein Vertragstest abdecken will.
- Aufwand: mittel. OPTIONS/HEAD oder das Auflisten bekannter Pfade gegen die
  live API abfragen, Ergebnis als neuer Finding-Code (Warnung, um verträglich
  zu sein) melden.
- Warum: schließt die wichtigste inhaltliche Lücke; reine Fehlermeldungen sind
  unsichtbar, dieser Punkt ist öffentlich sichtbarer Nutzen.

### 4. `exclusiveMinimum`/`exclusiveMaximum`/`const`, Format `date` und `byte`

- Nutzen: `_FORMAT_CHECKS` kennt `date-time`, `uuid`, `email`, `uri`
  (`checker.py:107`); `date` und `byte` sind in realen Specs häufig und heute
  stille Nichtigkeiten. Gleiches gilt für `exclusiveMinimum`/`Maximum` aus 2.
- Aufwand: klein (`_is_date`, `_is_base64`, je 2–3 Tests).
- Warum: reine Warnungs-Erweiterung, kein Interface-Risiko.

### 5. Rekursions-/Komplexitätsgrenzen für 1e konfigurierbar machen

- Nutzen: in `bestand.md` e/3/e/4 fehlt ein Größen-Limit zwar nicht mehr
  (50 MB fest), aber Timeout (20 s) und Maximalgröße sind hart kodiert und der
  Redirect-Folge hat keine Grenze. Ein `--spec-max-bytes` und ein
  konfigurierbarer Download-Timeout machen das Werkzeug für fremde Specs
  steuerbar.
- Aufwand: klein (zwei Optionen, zwei Tests).
- Warum: Sicherheitspflege ohne Bruch, einfach testbar.

### 6. Coverage-Messung und -Gate in CI

- Nutzen: `bestand.md` b zeigt: es gibt keine Abdeckungszahl. Ein
  `pytest --cov` (ab Werkzeug-Einrichtung) und ein Unterlauf-Gate verhindern,
  dass Tests langsamer werden als die Kernpfade. Sinnvoll kombiniert mit 7.
- Aufwand: mittel (neue Dev-Dependenz, CI-Schritt, Bericht im Upload).
- Warum: Qualitätssicherung mit sofort sichtbarem Effekt, aber geringerer
  Außenwirkung als 1–5 — deshalb hier.

### 7. Typprüfung (mypy) in die CI aufnehmen

- Nutzen: `bestand.md` e/13: CI fährt nur `pytest`. Seit dieser Pflege sind
  alle Annotationen vorhanden; eine Typprüfung wäre jetzt erst wirksam und
  kostengünstig, statt nachzuziehen. Ein mypy-Lauf (strict, nur
  `src/specsentinel`) findet Klassen von Fehlern, die Tests nicht sehen.
- Aufwand: klein bis mittel (neue Dev-Dependenz, ein CI-Call, kleinere Fixes).
- Warum: baut direkt auf TEIL 2c auf; erst nachdem die Annotationen fertig
  sind, ist der Lauf aussagekräftig.

### 8. Bessere Fehlermeldungen in den übrigen Pfaden (Baseline, Params-Datei)

- Nutzen: `baseline.py` und `_load_params_file` melden mal mit Pfad, mal ohne.
  Die in TEIL 2d eingeführte „(in paths./x.get.responses)"-Schreibweise sollte
  einheitlich auch in Fehlern des Laders („Params file ist nicht JSON/YAML")
  stehen, damit der Nutzer weiß, wo er schauen muss.
- Aufwand: klein (Textbausteine, 2–3 Test-Assertions).
- Warum: Konsistenz-Schliff nach 2d, geringes Risiko.

### 9. GitHub Action: Summary/Annotations ausgeben

- Nutzen: der Action-Smoke-Test existiert, aber die Action selbst zeigt
  Findings nur im Schritt-Log. GitHub Actions-Annotationen (Files/Schritt) und
  ein kurzes Job-Summary-Markdown machen Drift im PR sofort sichtbar, ohne
  dass jemand Logs öffnet.
- Aufwand: mittel (Action-Skript erweitern, 2 Staffel-Tests im
  `action_test.yml`-Stil; allein nicht im `pytest`-Lauf prüfbar).
- Warum: erhöht die Sichtbarkeit (siehe Teil 3), ohne die CLI zu ändern.

### 10. Release-Kette vollenden (Tag, PyPI, README-Branch)

- Nutzen: `bestand.md` d: Repo steht auf 0.3.0, PyPI auf 0.2.0, Tags bis
  v0.2.0. README verweist auf `@v0.3.0`, der Tag existiert nicht. Eine
  vollständige Release-Kette (Release → `publish.yml` → Tag) macht die
  Versprechen der Doku wahr.
- Aufwand: klein (ein Release), aber Prozess, kein Code.
- Warum: kein Feature, aber die Grundlage für die Sichtbarkeit unten.

## Wie SpecSentinel sichtbarer wird

1. **GitHub Action in den Marketplace aufnehmen** — `action.yml` und
   `action_test.yml` existieren. Ein Marketplace-Eintrag (METADATA, korrektes
   README-Badge, Versioned Tags) ist der größte Hebel: der erste Einstieg in
   solche Tools ist fast immer die Action.
2. **README mit einem „30-Sekunden-Demo"** — ein animiertes GIF oder eine
   konkrete „Before/After": Spec roh, `specsentinel --write-baseline`, dann
   ein neues Feld → sofortiger roter Build. Die verlinkte Video/GIF-Demo im
   README (und auf der PyPI-Seite, die den README spiegelt) senkt die
   Einstiegshürde.
3. **Reale Spezifikationen weiterhin regelmäßig testen und präsentieren** —
   `tools/spec_smoke.py` und `docs/smoke_results.md` sind starkes Social
   Proof. Sie regelmäßig zu aktualisieren und auf der Landing zu verlinken
   („gegen Petstore, GitHub, Stripe geprüft") macht Vertrauen greifbar — und
   deckt zugleich Regressionen ab.