# Portfolio-Agent App (Topf A & Topf B)

Lokale Streamlit-App für den Schweizer Privatanleger mit zwei strikt getrennten Töpfen.

## Voraussetzungen

- Python 3.9+
- Internetverbindung (für Live-Kurse und News)

## Installation

```bash
cd /pfad/zur/app
pip install -r requirements.txt
```

## Start

```bash
streamlit run portfolio_app.py
```

Die App öffnet sich automatisch im Browser (meist http://localhost:8501).

## Funktionen

- **Internet-Status** ganz oben (grün = online, rot = offline)
- Bei Offline: **keine Empfehlungen** (auch nicht aus Cache)
- Topf A: 10’000 CHF Startkapital, langfristig (10+ Jahre), Wachstums-Profil
- Topf B: max. 1’000 CHF Verlustbudget, kurzer Horizont
- Positionen hinzufügen über die Sidebar
- Risikolevel & Horizont jederzeit anpassbar
- Update-Button holt Kurse (yfinance) + News (Google News RSS)
- Regelbasierte Empfehlungen + Risiko-Checks

## Daten

Alle Einstellungen und Positionen werden lokal in `portfolio_data.json` gespeichert.

## Wichtige Hinweise

- Keine Anlageberatung – nur Entscheidungsunterstützung
- Du entscheidest immer selbst
- Die App greift auf öffentliche Quellen zu (Yahoo Finance, Google News)
- Keine API-Keys nötig
