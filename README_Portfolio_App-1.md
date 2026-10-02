# Portfolio-Agent App v2

Lokale / Streamlit-Cloud App für Schweizer Privatanleger mit zwei strikt getrennten Töpfen.

## Neu in Version 2

- **Vordefinierte Instrumentenliste** – keine freien Ticker mehr, nur auswählbare ETFs, Aktien, Gold/Silber und Bargeld
- Preis wird **automatisch** per Live-Kurs vorausgefüllt
- Deutlich klarere, regelbasierte Empfehlungen (Halten / Nachkaufen / Teilverkauf / Stop beachten)
- Gold & andere Edelmetalle + Bargeld (CHF) integriert
- Moderneres, aufgeräumteres Interface
- Strikte Internet-Prüfung: Offline → keine Empfehlungen

## Dateien

- `portfolio_app.py` – die App
- `requirements.txt` – Abhängigkeiten

## Installation (lokal)

```bash
pip install -r requirements.txt
streamlit run portfolio_app.py
```

## Streamlit Cloud (für Smartphone)

1. Beide Dateien in ein öffentliches GitHub-Repo legen
2. Auf https://share.streamlit.io einloggen
3. New app → Repo wählen → Main file: `portfolio_app.py` → Deploy
4. Öffentlichen Link auf dem Smartphone öffnen

## Wichtige Hinweise

- Daten werden in `portfolio_data.json` gespeichert (lokal persistent, auf Streamlit Cloud flüchtig)
- Keine Anlageberatung – nur Entscheidungsunterstützung
- Nur die in der App definierten Instrumente sind erlaubt
