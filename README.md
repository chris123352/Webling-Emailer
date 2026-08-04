# Webling-Emailer

Eine zuverlässige Grundlage für Automatisierungen rund um **Webling Cloud**. Das Projekt wird schrittweise um Geburtstagsmails, Mitgliedsjubiläen, Adminberichte, Health Checks und weitere Vereinsprozesse erweitert.

Die erste Version enthält bewusst noch **keine Webling-API-Integration**. Sie stellt Konfiguration, strukturiertes Logging, Tests und einen automatischen GitHub-Workflow bereit.

## Einrichtung

Voraussetzung ist Python 3.11 oder neuer.

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -e ".[dev]"
copy config.example.yml config.yml
```

Ergänze anschließend `config.yml` oder setze die dort verwendeten Umgebungsvariablen und starte die Anwendung:

```bash
python -m app.main
```

Tests und Code-Checks:

```bash
pytest
ruff check .
```

## Konfiguration und Geheimnisse

`config.example.yml` ist die Vorlage für die lokale Konfiguration. Die Datei `config.yml` ist absichtlich in `.gitignore` eingetragen.

**API-Keys, Passwörter und andere Geheimnisse niemals committen.** Verwende lokal Umgebungsvariablen oder eine nicht versionierte `config.yml`.

Unterstützte Umgebungsvariablen:

- `WEBLING_API_KEY`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`
- `ADMIN_EMAIL`

## GitHub Secrets vorbereiten

Lege im GitHub-Repository unter **Settings → Secrets and variables → Actions** folgende Secrets an:

- `WEBLING_API_KEY`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `ADMIN_EMAIL`

Der Workflow erzeugt daraus zur Laufzeit eine lokale `config.yml`. Er kann manuell gestartet werden und läuft täglich um 08:00 Uhr in der Zeitzone Europe/Berlin. Die Sommer- und Winterzeit wird berücksichtigt.
