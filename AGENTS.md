Projekt: SpecSentinel, Python CLI, vergleicht eine laufende API mit ihrer OpenAPI Spezifikation.
Exit Codes: 0 Übereinstimmung, 1 Drift, 2 Prüfung nicht möglich.

Regeln:
1. Führe Befehle immer im aktuellen Ordner aus. Gib nie einen Arbeitsordner oder einen absoluten Pfad an. Nutze nur relative Pfade.
2. Commit und Push auf den Branch improve-real-world sind erlaubt, auf main nie.
3. Nach jeder Änderung python -m pytest -q laufen lassen und die echte Ausgabe zeigen.
4. Keine Behauptung in README, Tests oder Beiträgen, die nicht durch einen Lauf belegt ist.
5. README und Code Kommentare auf Englisch.
6. Nutze die virtuelle Umgebung .venv (schon aktiv). Installiere nichts ohne Grund.
