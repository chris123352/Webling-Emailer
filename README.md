# Webling-Emailer

Eine zuverlässige Grundlage für Automatisierungen rund um **Webling Cloud**. Das Projekt wird schrittweise um Geburtstagsmails, Mitgliedsjubiläen, Adminberichte, Health Checks und weitere Vereinsprozesse erweitert.

Die Anwendung verbindet sich lesend mit der Webling-API, erzeugt wöchentliche Vorstandsberichte und stellt Konfiguration, strukturiertes Logging, Tests und einen automatischen GitHub-Workflow bereit.

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

Trage dafür unter `webling.url` die Basis-URL deiner Webling-Instanz ein, zum Beispiel
`https://mein-verein.webling.ch`. Der Client ergänzt den API-Pfad `/api/1` automatisch.

Für eine rein lesende Verbindungskontrolle steht der Diagnosemodus zur Verfügung:

```bash
python -m app.main diagnostic
```

Er prüft den API-Zugang, zählt abrufbare Mitglieder und kontrolliert die Felder eines
Beispielmitglieds. Dabei werden keine Webling-Daten verändert und keine E-Mails versendet.

Der sichere Standardmodus `diagnostic` benötigt nur `webling.url` und `WEBLING_API_KEY`.
Der spätere produktive Modus wird mit `python -m app.main production` gestartet und verlangt
zusätzlich die SMTP- sowie Admin-Konfiguration.

Eine ebenfalls rein lesende Geburtstagsvorschau kann mit folgendem Befehl gestartet werden:

```bash
python -m app.main birthday-test
```

Sie erkennt heutige Geburtstage und berechnet das Alter, versendet aber keine E-Mails.

## Mail-Testmodus

`python -m app.main birthday-send-test` erstellt für heutige Geburtstage echte HTML- und
Text-E-Mails. Der Modus startet nur mit aktivierter Umleitung und leitet jede Nachricht an
`test.recipients` um. Die ursprüngliche Empfängeradresse erscheint ausschließlich im Log;
ein Produktivversand ist nicht implementiert.

## Wöchentlicher Vorstandsbericht

Der Workflow startet sonntags um 08:00 Uhr (Europe/Berlin) den Modus
`python -m app.main weekly-report`. Dieser versendet eine einzige HTML- und Text-E-Mail an die
fest hinterlegten Empfänger unter `weekly_report.recipients` mit allen Geburtstagen und
Mitgliedsjubiläen von Montag bis Sonntag der folgenden Woche. Auch ohne Treffer wird ein
Bericht mit dem Hinweis versendet, dass nichts ansteht. Mitglieder erhalten dabei nie eine Mail.

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
- `WEBLING_URL`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`
- `SMTP_FROM_ADDRESS` (optional; sonst wird `SMTP_USERNAME` als Absender verwendet)
- `ADMIN_EMAIL`

## GitHub Secrets vorbereiten

Lege im GitHub-Repository unter **Settings → Secrets and variables → Actions** folgende Secrets an:

- `WEBLING_API_KEY`
- `WEBLING_URL`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_ADDRESS` (optional)
- `ADMIN_EMAIL`

Der Workflow erzeugt daraus zur Laufzeit eine lokale `config.yml`. Er kann manuell gestartet werden und läuft sonntags um 08:00 Uhr in der Zeitzone Europe/Berlin. Die Sommer- und Winterzeit wird berücksichtigt.

## Webling-API

Der Client verwendet den von Webling dokumentierten `apikey`-HTTP-Header. Der API-Key wird ausschließlich aus der Umgebungsvariable `WEBLING_API_KEY` geladen und niemals in einer Konfigurationsdatei abgelegt.
