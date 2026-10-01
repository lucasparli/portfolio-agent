#!/usr/bin/env python3
"""
Portfolio-Agent App – Topf A (Anlage) & Topf B (Trading)
Schweizer Privatanleger | Streamlit | Lokale Ausführung
"""

import streamlit as st
import yfinance as yf
import json
import os
import requests
import feedparser
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

# ---------------------------------------------------------------------------
# Konfiguration & Dateipfade
# ---------------------------------------------------------------------------
DATA_FILE = "portfolio_data.json"
DEFAULT_DATA = {
    "topf_a": {
        "startkapital": 10000.0,
        "holdings": {},  # ticker: {"shares": float, "avg_price": float, "name": str}
        "risk_level": "Wachstum",
        "horizon": "10+ Jahre",
        "ziel_allokation": {
            "VWCE.DE": 0.75,   # FTSE All-World Acc (Beispiel)
            "EIMI.L": 0.15,    # Emerging Markets
            "Cash": 0.10
        }
    },
    "topf_b": {
        "max_verlustbudget": 1000.0,
        "realisierter_verlust": 0.0,
        "holdings": {},  # ticker: {"shares": float, "avg_price": float, "stop_loss": float, "name": str, "entry_date": str}
        "risk_level": "Strikt begrenzt",
        "horizon": "Kurz (Tage–Monate)",
        "max_positionen": 4,
        "max_risiko_pro_trade_pct": 0.25  # 25 % des noch verfügbaren Budgets
    },
    "last_update": None,
    "version": "1.0"
}

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------
def load_data() -> Dict[str, Any]:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Fehlende Keys ergänzen
            for k, v in DEFAULT_DATA.items():
                if k not in data:
                    data[k] = v
            return data
        except Exception:
            return DEFAULT_DATA.copy()
    return DEFAULT_DATA.copy()


def save_data(data: Dict[str, Any]) -> None:
    data["last_update"] = datetime.now().isoformat()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def check_internet(timeout: float = 4.0) -> bool:
    """Prüft echte Internetverbindung. Kein Cache, kein Fallback."""
    test_urls = [
        "https://finance.yahoo.com",
        "https://www.google.com",
        "https://query1.finance.yahoo.com"
    ]
    for url in test_urls:
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code < 500:
                return True
        except Exception:
            continue
    return False


def get_price_info(ticker: str) -> Optional[Dict[str, Any]]:
    """Holt aktuelle Kursdaten via yfinance. Gibt None zurück bei Fehler."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        hist = t.history(period="5d")
        if hist.empty:
            return None
        last_close = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else last_close
        change_pct = ((last_close - prev_close) / prev_close * 100) if prev_close else 0.0
        return {
            "price": last_close,
            "change_pct": change_pct,
            "currency": info.get("currency", "USD"),
            "name": info.get("shortName") or info.get("longName") or ticker,
            "market_cap": info.get("marketCap"),
            "pe": info.get("trailingPE"),
        }
    except Exception:
        return None


def get_news(ticker: str, max_items: int = 5) -> list:
    """Holt aktuelle News-Überschriften via Google News RSS (kostenlos, kein Key)."""
    try:
        # Deutsch / Schweiz priorisieren
        query = f"{ticker} Aktie OR stock"
        url = f"https://news.google.com/rss/search?q={query}&hl=de&gl=CH&ceid=CH:de"
        feed = feedparser.parse(url)
        news = []
        for entry in feed.entries[:max_items]:
            news.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", "")[:16] if entry.get("published") else ""
            })
        return news
    except Exception:
        return []


def calc_topf_a_value(holdings: Dict, prices: Dict[str, float]) -> float:
    total = 0.0
    for t, h in holdings.items():
        if t in prices:
            total += h["shares"] * prices[t]
    return total


def calc_open_risk_topf_b(holdings: Dict, prices: Dict[str, float]) -> float:
    """Schätzt aktuelles offenes Risiko (Distanz zum Stop-Loss)."""
    risk = 0.0
    for t, h in holdings.items():
        if t in prices and h.get("stop_loss"):
            current = prices[t]
            stop = h["stop_loss"]
            if current > stop:  # Long-Annahme
                risk += h["shares"] * (current - stop)
            else:
                risk += h["shares"] * abs(current - stop)  # bereits im Verlust
    return risk


# ---------------------------------------------------------------------------
# Streamlit App
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Portfolio-Agent | Topf A & B",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Daten laden
if "data" not in st.session_state:
    st.session_state.data = load_data()

data = st.session_state.data

# ----- Internet-Status (ganz oben, unverzichtbar) -----
internet_ok = check_internet()

col_status, col_time = st.columns([3, 1])
with col_status:
    if internet_ok:
        st.success("✅ Internetverbindung aktiv – Live-Daten möglich")
    else:
        st.error("🚨 KEINE Internetverbindung – Empfehlungen sind deaktiviert. Es werden keine gespeicherten oder geratenen Empfehlungen ausgegeben.")
with col_time:
    st.caption(f"Stand: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

st.title("Portfolio-Agent – Zwei Töpfe")
st.caption("Topf A = langfristiger Vermögensaufbau · Topf B = begrenztes Trading-Budget")

# ----- Sidebar: Einstellungen & Positionen hinzufügen -----
with st.sidebar:
    st.header("⚙️ Einstellungen")

    st.subheader("Topf A – Anlage")
    data["topf_a"]["risk_level"] = st.selectbox(
        "Risikolevel Topf A",
        ["Konservativ", "Wachstum", "Dynamisch"],
        index=["Konservativ", "Wachstum", "Dynamisch"].index(data["topf_a"].get("risk_level", "Wachstum"))
    )
    data["topf_a"]["horizon"] = st.selectbox(
        "Horizont Topf A",
        ["5–7 Jahre", "10+ Jahre", "15+ Jahre"],
        index=["5–7 Jahre", "10+ Jahre", "15+ Jahre"].index(data["topf_a"].get("horizon", "10+ Jahre"))
    )
    data["topf_a"]["startkapital"] = st.number_input(
        "Startkapital Topf A (CHF)",
        min_value=1000.0,
        value=float(data["topf_a"].get("startkapital", 10000.0)),
        step=500.0
    )

    st.subheader("Topf B – Trading")
    data["topf_b"]["risk_level"] = st.selectbox(
        "Risikolevel Topf B",
        ["Sehr strikt", "Strikt begrenzt", "Moderat"],
        index=["Sehr strikt", "Strikt begrenzt", "Moderat"].index(data["topf_b"].get("risk_level", "Strikt begrenzt"))
    )
    data["topf_b"]["horizon"] = st.selectbox(
        "Horizont Topf B",
        ["Sehr kurz (Tage)", "Kurz (Tage–Monate)", "Bis 3 Monate"],
        index=["Sehr kurz (Tage)", "Kurz (Tage–Monate)", "Bis 3 Monate"].index(data["topf_b"].get("horizon", "Kurz (Tage–Monate)"))
    )
    data["topf_b"]["max_verlustbudget"] = st.number_input(
        "Max. Verlustbudget Topf B (CHF)",
        min_value=100.0,
        value=float(data["topf_b"].get("max_verlustbudget", 1000.0)),
        step=100.0
    )

    st.divider()
    st.subheader("➕ Position hinzufügen")

    topf_wahl = st.radio("Topf", ["Topf A", "Topf B"], horizontal=True)
    new_ticker = st.text_input("Ticker (z. B. VWCE.DE, AAPL, NESN.SW)").upper().strip()
    new_shares = st.number_input("Stückzahl", min_value=0.01, value=1.0, step=0.1)
    new_price = st.number_input("Durchschnittspreis (in Originalwährung)", min_value=0.01, value=100.0, step=0.1)
    new_stop = None
    if topf_wahl == "Topf B":
        new_stop = st.number_input("Stop-Loss Preis (Pflicht für Topf B)", min_value=0.01, value=90.0, step=0.1)

    if st.button("Position speichern"):
        if new_ticker:
            target = "topf_a" if topf_wahl == "Topf A" else "topf_b"
            if target == "topf_b" and len(data["topf_b"]["holdings"]) >= data["topf_b"].get("max_positionen", 4):
                st.error("Maximale Anzahl Positionen in Topf B erreicht.")
            else:
                entry = {
                    "shares": float(new_shares),
                    "avg_price": float(new_price),
                    "name": new_ticker,
                    "entry_date": datetime.now().strftime("%Y-%m-%d")
                }
                if new_stop is not None:
                    entry["stop_loss"] = float(new_stop)
                data[target]["holdings"][new_ticker] = entry
                save_data(data)
                st.session_state.data = data
                st.success(f"{new_ticker} in {topf_wahl} gespeichert.")
                st.rerun()

    if st.button("💾 Alle Einstellungen speichern"):
        save_data(data)
        st.session_state.data = data
        st.success("Gespeichert.")

# ----- Hauptbereich -----
tab_a, tab_b, tab_regeln = st.tabs(["📈 Topf A – Anlage", "⚡ Topf B – Trading", "🛡️ Risiko-Regeln"])

# ===================== TOPF A =====================
with tab_a:
    st.subheader("Topf A – Langfristiger Vermögensaufbau")
    st.write(f"**Risiko:** {data['topf_a']['risk_level']}  |  **Horizont:** {data['topf_a']['horizon']}  |  **Startkapital:** {data['topf_a']['startkapital']:,.0f} CHF")

    holdings_a = data["topf_a"]["holdings"]

    if not holdings_a:
        st.info("Topf A ist noch leer.")
        if internet_ok:
            st.markdown("""
            **Vorschlag für den Start (Wachstums-Profil, 10+ Jahre):**
            - 70–80 % Globaler Aktienmarkt → z. B. **VWCE.DE** (FTSE All-World Acc) oder **SSAC.L**
            - 10–15 % Schwellenländer → z. B. **EIMI.L** oder **IS3N.DE**
            - 5–10 % optional Small-Cap / Value später
            - Rest als Cash-Puffer

            Füge die ersten Positionen über die Sidebar hinzu.
            """)
        else:
            st.warning("Offline – keine Startvorschläge möglich.")
    else:
        # Kurse holen nur wenn online
        prices_a = {}
        if internet_ok:
            with st.spinner("Kurse werden geladen..."):
                for t in holdings_a:
                    info = get_price_info(t)
                    if info:
                        prices_a[t] = info["price"]
                        holdings_a[t]["name"] = info.get("name", t)
                        holdings_a[t]["_change"] = info.get("change_pct", 0)
                        holdings_a[t]["_currency"] = info.get("currency", "")
                    else:
                        prices_a[t] = holdings_a[t]["avg_price"]  # Fallback nur Anzeige, keine Empf.
        else:
            for t in holdings_a:
                prices_a[t] = holdings_a[t]["avg_price"]

        # Tabelle
        rows = []
        total_value = 0.0
        for t, h in holdings_a.items():
            val = h["shares"] * prices_a.get(t, h["avg_price"])
            total_value += val
            rows.append({
                "Ticker": t,
                "Name": h.get("name", t),
                "Stück": h["shares"],
                "Ø Preis": h["avg_price"],
                "Aktuell": round(prices_a.get(t, 0), 2),
                "Wert": round(val, 2),
                "Δ %": round(h.get("_change", 0), 2)
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
        st.metric("Aktueller Gesamtwert (ca.)", f"{total_value:,.2f}")

        # Update-Button & Empfehlungen
        if st.button("🔄 Update & Empfehlungen Topf A", disabled=not internet_ok, key="update_a"):
            if not internet_ok:
                st.error("Keine Internetverbindung – es werden keine Empfehlungen ausgegeben.")
            else:
                st.markdown("### Empfehlungen Topf A")
                # Einfache Rebalancing-Logik
                if total_value > 0:
                    for t, h in holdings_a.items():
                        gewicht = (h["shares"] * prices_a.get(t, 0)) / total_value
                        st.write(f"**{t}**: aktuelles Gewicht ca. {gewicht*100:.1f} %")
                    st.info("Regel: Bei Abweichung > 5–7 % vom Zielgewicht → rebalancieren. "
                            "Kein aktives Stock-Picking. Kosten im Blick behalten (TER ≤ 0,25 %).")
                # News
                st.markdown("#### Aktuelle News zu den Positionen")
                for t in holdings_a:
                    news = get_news(t, max_items=3)
                    if news:
                        st.write(f"**{t}**")
                        for n in news:
                            st.markdown(f"- [{n['title']}]({n['link']}) ({n['published']})")
                    else:
                        st.caption(f"Keine aktuellen News für {t} gefunden.")

# ===================== TOPF B =====================
with tab_b:
    st.subheader("Topf B – Trading mit klarem Verlustbudget")
    budget = data["topf_b"]["max_verlustbudget"]
    real_loss = data["topf_b"].get("realisierter_verlust", 0.0)
    remaining_budget = max(0.0, budget - real_loss)

    st.write(f"**Risiko:** {data['topf_b']['risk_level']}  |  **Horizont:** {data['topf_b']['horizon']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Max. Verlustbudget", f"{budget:,.0f} CHF")
    c2.metric("Bereits realisiert", f"{real_loss:,.0f} CHF")
    c3.metric("Noch verfügbar", f"{remaining_budget:,.0f} CHF")

    holdings_b = data["topf_b"]["holdings"]

    if remaining_budget <= 0:
        st.error("🚨 Verlustbudget ausgeschöpft – keine neuen Trades erlaubt.")

    if not holdings_b:
        st.info("Topf B ist noch leer. Füge Positionen nur hinzu, wenn ein klarer Katalysator oder starkes Momentum vorhanden ist.")
        if internet_ok:
            st.markdown("""
            **Pflichtregeln Topf B:**
            - Maximal 3–4 offene Positionen
            - Pro Trade max. 20–25 % des noch verfügbaren Verlustbudgets riskieren
            - Jeder Trade braucht einen Stop-Loss
            - Kein Averaging-Down ohne neuen Katalysator
            """)
    else:
        prices_b = {}
        if internet_ok:
            with st.spinner("Kurse Topf B werden geladen..."):
                for t in holdings_b:
                    info = get_price_info(t)
                    if info:
                        prices_b[t] = info["price"]
                        holdings_b[t]["name"] = info.get("name", t)
                        holdings_b[t]["_change"] = info.get("change_pct", 0)
                    else:
                        prices_b[t] = holdings_b[t]["avg_price"]
        else:
            for t in holdings_b:
                prices_b[t] = holdings_b[t]["avg_price"]

        rows_b = []
        open_risk = 0.0
        for t, h in holdings_b.items():
            val = h["shares"] * prices_b.get(t, h["avg_price"])
            stop = h.get("stop_loss")
            risk_this = 0.0
            if stop and t in prices_b:
                risk_this = h["shares"] * max(0, prices_b[t] - stop) if prices_b[t] > stop else h["shares"] * abs(prices_b[t] - stop)
                open_risk += risk_this
            rows_b.append({
                "Ticker": t,
                "Stück": h["shares"],
                "Ø Preis": h["avg_price"],
                "Aktuell": round(prices_b.get(t, 0), 2),
                "Stop-Loss": stop,
                "Geschätztes Risiko": round(risk_this, 2),
                "Wert": round(val, 2),
                "Δ %": round(h.get("_change", 0), 2)
            })
        st.dataframe(pd.DataFrame(rows_b), use_container_width=True)
        st.metric("Geschätztes offenes Risiko", f"{open_risk:,.2f} CHF")

        if st.button("🔄 Update & Empfehlungen Topf B", disabled=not internet_ok, key="update_b"):
            if not internet_ok:
                st.error("Keine Internetverbindung – es werden keine Empfehlungen ausgegeben.")
            else:
                st.markdown("### Empfehlungen Topf B")
                if open_risk > remaining_budget:
                    st.error("Offenes Risiko übersteigt das noch verfügbare Budget → Positionen reduzieren oder Stops enger setzen.")
                elif remaining_budget < 100:
                    st.warning("Verlustbudget fast ausgeschöpft – sehr vorsichtig bleiben.")
                else:
                    st.success("Offenes Risiko innerhalb des Budgets.")
                st.info("Prüfe bei jeder Position: Ist der Katalysator / das Momentum noch intakt? "
                        "Zeit-Stop nach 4–8 Wochen ohne Fortschritt in Betracht ziehen.")

                st.markdown("#### News zu den Positionen")
                for t in holdings_b:
                    news = get_news(t, max_items=3)
                    if news:
                        st.write(f"**{t}**")
                        for n in news:
                            st.markdown(f"- [{n['title']}]({n['link']}) ({n['published']})")

# ===================== REGELN =====================
with tab_regeln:
    st.subheader("Verbindliche Risiko-Management-Regeln")
    st.markdown("""
### Topf A – Langfristig
- Breite Streuung (globaler Aktienkern 70–80 %)
- Nur ETFs mit TER ≤ 0,25 %
- Rebalancing einmal jährlich oder bei > 5–7 % Drift
- Keine Hebel, keine Derivate
- Bei Drawdowns > 30 %: nicht verkaufen, langfristig bleiben

### Topf B – Trading
- **Hartes Verlustbudget** (aktuell 1’000 CHF) – wird nie überschritten
- Pro Trade max. 20–25 % des noch verfügbaren Budgets riskieren
- Maximal 3–4 offene Positionen
- Stop-Loss bei jedem Trade Pflicht
- Kein Averaging-Down ohne neuen Katalysator
- Zeit-Stop: Positionen ohne Momentum nach 4–8 Wochen prüfen

### Übergreifend
- Strikte Trennung der beiden Töpfe
- Empfehlungen **nur** bei aktiver Internetverbindung
- Du entscheidest immer selbst – die App schlägt nur vor
""")

# Footer
st.divider()
st.caption("Portfolio-Agent v1.0 · Lokale App · Keine Anlageberatung · Nur Entscheidungsunterstützung")
