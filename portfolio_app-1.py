#!/usr/bin/env python3
"""
Portfolio-Agent App v2 – Topf A (Anlage) & Topf B (Trading)
Schweizer Privatanleger | Moderner, intuitiver, mit vordefinierter Instrumentenliste
"""

import streamlit as st
import yfinance as yf
import json
import os
import requests
import feedparser
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, List

# ---------------------------------------------------------------------------
# Vordefinierte Instrumentenliste (nur diese dürfen gewählt werden)
# ---------------------------------------------------------------------------
INSTRUMENTS = {
    # === Topf A – Kern (ETFs) ===
    "VWCE.DE": {
        "name": "Vanguard FTSE All-World Acc",
        "type": "etf",
        "topf": ["A"],
        "desc": "Globaler Aktienmarkt (Developed + Emerging)",
        "currency": "EUR"
    },
    "SSAC.L": {
        "name": "iShares MSCI ACWI Acc",
        "type": "etf",
        "topf": ["A"],
        "desc": "All Country World Index",
        "currency": "USD"
    },
    "EIMI.L": {
        "name": "iShares Core MSCI EM IMI Acc",
        "type": "etf",
        "topf": ["A"],
        "desc": "Schwellenländer",
        "currency": "USD"
    },
    "IS3N.DE": {
        "name": "iShares Core MSCI EM IMI Acc",
        "type": "etf",
        "topf": ["A"],
        "desc": "Schwellenländer (Xetra)",
        "currency": "EUR"
    },
    "CSPX.L": {
        "name": "iShares Core S&P 500 Acc",
        "type": "etf",
        "topf": ["A"],
        "desc": "US Large Caps",
        "currency": "USD"
    },
    "EXW1.DE": {
        "name": "iShares Core Euro Stoxx 50",
        "type": "etf",
        "topf": ["A"],
        "desc": "Eurozone Large Caps",
        "currency": "EUR"
    },
    "SXR8.DE": {
        "name": "iShares Core S&P 500 Acc (EUR)",
        "type": "etf",
        "topf": ["A"],
        "desc": "S&P 500 thesaurierend",
        "currency": "EUR"
    },

    # === Edelmetalle ===
    "4GLD.DE": {
        "name": "Xetra-Gold",
        "type": "metal",
        "topf": ["A", "B"],
        "desc": "Physisch hinterlegtes Gold (Xetra)",
        "currency": "EUR"
    },
    "SGLD.L": {
        "name": "Invesco Physical Gold",
        "type": "metal",
        "topf": ["A", "B"],
        "desc": "Physisches Gold ETC",
        "currency": "USD"
    },
    "IGLN.L": {
        "name": "iShares Physical Gold ETC",
        "type": "metal",
        "topf": ["A", "B"],
        "desc": "Physisches Gold",
        "currency": "USD"
    },
    "SLVR.L": {
        "name": "Invesco Physical Silver",
        "type": "metal",
        "topf": ["A", "B"],
        "desc": "Physisches Silber ETC",
        "currency": "USD"
    },

    # === Cash ===
    "CASH.CHF": {
        "name": "Bargeld (CHF)",
        "type": "cash",
        "topf": ["A", "B"],
        "desc": "Schweizer Franken Liquidität",
        "currency": "CHF"
    },

    # === Topf B – liquide Einzeltitel / Trading-Ideen (Beispiele) ===
    "NESN.SW": {
        "name": "Nestlé",
        "type": "stock",
        "topf": ["B"],
        "desc": "Schweizer Defensiv-Aktie",
        "currency": "CHF"
    },
    "ROG.SW": {
        "name": "Roche",
        "type": "stock",
        "topf": ["B"],
        "desc": "Pharma",
        "currency": "CHF"
    },
    "NOVN.SW": {
        "name": "Novartis",
        "type": "stock",
        "topf": ["B"],
        "desc": "Pharma",
        "currency": "CHF"
    },
    "UBSG.SW": {
        "name": "UBS Group",
        "type": "stock",
        "topf": ["B"],
        "desc": "Schweizer Bank",
        "currency": "CHF"
    },
    "AAPL": {
        "name": "Apple",
        "type": "stock",
        "topf": ["B"],
        "desc": "US Tech",
        "currency": "USD"
    },
    "MSFT": {
        "name": "Microsoft",
        "type": "stock",
        "topf": ["B"],
        "desc": "US Tech",
        "currency": "USD"
    },
    "NVDA": {
        "name": "NVIDIA",
        "type": "stock",
        "topf": ["B"],
        "desc": "Halbleiter / AI",
        "currency": "USD"
    },
    "TSLA": {
        "name": "Tesla",
        "type": "stock",
        "topf": ["B"],
        "desc": "EV / Momentum",
        "currency": "USD"
    },
    "AMZN": {
        "name": "Amazon",
        "type": "stock",
        "topf": ["B"],
        "desc": "E-Commerce / Cloud",
        "currency": "USD"
    },
    "GOOGL": {
        "name": "Alphabet",
        "type": "stock",
        "topf": ["B"],
        "desc": "Search / Cloud / AI",
        "currency": "USD"
    },
}

# Ziel-Allokation für Topf A (Wachstum 10+ Jahre)
TARGET_A = {
    "VWCE.DE": 0.70,
    "EIMI.L": 0.15,
    "4GLD.DE": 0.05,   # kleiner Gold-Anteil als Absicherung
    "CASH.CHF": 0.10
}

DATA_FILE = "portfolio_data.json"

DEFAULT_DATA = {
    "topf_a": {
        "startkapital": 10000.0,
        "holdings": {},
        "risk_level": "Wachstum",
        "horizon": "10+ Jahre"
    },
    "topf_b": {
        "max_verlustbudget": 1000.0,
        "realisierter_verlust": 0.0,
        "holdings": {},
        "risk_level": "Strikt begrenzt",
        "horizon": "Kurz (Tage–Monate)",
        "max_positionen": 4
    },
    "last_update": None,
    "version": "2.0"
}

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------
def load_data() -> Dict[str, Any]:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in DEFAULT_DATA.items():
                if k not in data:
                    data[k] = v
            return data
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_DATA))  # deep copy


def save_data(data: Dict[str, Any]) -> None:
    data["last_update"] = datetime.now().isoformat()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def check_internet(timeout: float = 3.5) -> bool:
    for url in ["https://finance.yahoo.com", "https://www.google.com"]:
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code < 500:
                return True
        except Exception:
            continue
    return False


def get_price_info(ticker: str) -> Optional[Dict[str, Any]]:
    if ticker == "CASH.CHF":
        return {"price": 1.0, "change_pct": 0.0, "currency": "CHF", "name": "Bargeld (CHF)"}
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if hist.empty:
            return None
        last = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else last
        change = ((last - prev) / prev * 100) if prev else 0.0
        info = t.info
        return {
            "price": last,
            "change_pct": change,
            "currency": info.get("currency") or INSTRUMENTS.get(ticker, {}).get("currency", "USD"),
            "name": info.get("shortName") or INSTRUMENTS.get(ticker, {}).get("name", ticker)
        }
    except Exception:
        return None


def get_news(ticker: str, max_items: int = 4) -> List[Dict]:
    if ticker == "CASH.CHF":
        return []
    try:
        q = INSTRUMENTS.get(ticker, {}).get("name", ticker).replace(" ", "+")
        url = f"https://news.google.com/rss/search?q={q}+Aktie+OR+stock&hl=de&gl=CH&ceid=CH:de"
        feed = feedparser.parse(url)
        return [{
            "title": e.get("title", ""),
            "link": e.get("link", ""),
            "published": (e.get("published") or "")[:16]
        } for e in feed.entries[:max_items]]
    except Exception:
        return []


def instrument_options(topf: str) -> Dict[str, str]:
    """Gibt {anzeige: ticker} für Selectbox zurück."""
    opts = {}
    for t, meta in INSTRUMENTS.items():
        if topf in meta["topf"] or "A" in meta["topf"] and "B" in meta["topf"]:
            label = f"{meta['name']}  ({t})  · {meta['type'].upper()}"
            opts[label] = t
    return opts


def calc_portfolio_value(holdings: Dict, prices: Dict[str, float]) -> float:
    return sum(h["shares"] * prices.get(t, h.get("avg_price", 0)) for t, h in holdings.items())


def generate_recommendations_a(holdings: Dict, prices: Dict[str, float], total_value: float, internet_ok: bool) -> List[str]:
    recs = []
    if not internet_ok:
        return ["Keine Empfehlungen möglich – Internetverbindung fehlt."]

    if total_value <= 0 or not holdings:
        recs.append("Topf A ist leer. Empfohlener Start (Wachstum, 10+ Jahre):")
        recs.append("• 70 % VWCE.DE (FTSE All-World)")
        recs.append("• 15 % EIMI.L oder IS3N.DE (Emerging Markets)")
        recs.append("• 5 % 4GLD.DE (Xetra-Gold) als Absicherung")
        recs.append("• 10 % CASH.CHF als Liquiditätspuffer")
        return recs

    # Allokations-Drift
    for ticker, target_pct in TARGET_A.items():
        current_val = 0.0
        if ticker in holdings and ticker in prices:
            current_val = holdings[ticker]["shares"] * prices[ticker]
        current_pct = current_val / total_value if total_value > 0 else 0
        drift = current_pct - target_pct
        name = INSTRUMENTS.get(ticker, {}).get("name", ticker)

        if abs(drift) > 0.06:  # > 6 %
            if drift > 0:
                recs.append(f"**{name}** ({ticker}): Übergewichtet ({current_pct*100:.1f} % vs Ziel {target_pct*100:.0f} %). → Teilverkauf / Rebalancing prüfen.")
            else:
                recs.append(f"**{name}** ({ticker}): Untergewichtet ({current_pct*100:.1f} % vs Ziel {target_pct*100:.0f} %). → Nachkauf mit neuem Geld sinnvoll.")

    # Gold-Hinweis
    gold_val = sum(
        holdings[t]["shares"] * prices.get(t, 0)
        for t in holdings if INSTRUMENTS.get(t, {}).get("type") == "metal"
    )
    gold_pct = gold_val / total_value if total_value > 0 else 0
    if gold_pct < 0.03:
        recs.append("Gold-Anteil sehr niedrig. Ein kleiner physischer Gold-ETC (z. B. 4GLD.DE) kann als Absicherung sinnvoll sein.")

    if not recs:
        recs.append("Aktuelle Allokation liegt nah am Ziel. → Halten und jährliches Rebalancing abwarten.")

    return recs


def generate_recommendations_b(holdings: Dict, prices: Dict[str, float], remaining_budget: float, open_risk: float, internet_ok: bool) -> List[str]:
    recs = []
    if not internet_ok:
        return ["Keine Empfehlungen möglich – Internetverbindung fehlt."]

    if remaining_budget <= 0:
        recs.append("🚨 Verlustbudget vollständig ausgeschöpft. Keine neuen Positionen. Bestehende Positionen eng überwachen / reduzieren.")
        return recs

    if not holdings:
        recs.append("Topf B ist leer. Nur handeln bei klarem Katalysator oder starkem Momentum.")
        recs.append(f"Noch verfügbares Risiko-Budget: {remaining_budget:,.0f} CHF.")
        recs.append("Max. 20–25 % des Budgets pro Trade riskieren.")
        return recs

    if open_risk > remaining_budget * 0.9:
        recs.append("Offenes Risiko liegt nahe am Limit. → Keine neuen Trades. Stops enger setzen oder Positionen verkleinern.")

    for t, h in holdings.items():
        price = prices.get(t)
        if price is None:
            continue
        avg = h.get("avg_price", price)
        pnl_pct = (price - avg) / avg * 100 if avg else 0
        stop = h.get("stop_loss")
        name = INSTRUMENTS.get(t, {}).get("name", t)

        if stop and price <= stop * 1.02:
            recs.append(f"**{name}** ({t}): Nähe zum Stop-Loss. → Verkauf / Stop eng überwachen.")
        elif pnl_pct > 35:
            recs.append(f"**{name}** ({t}): +{pnl_pct:.1f} %. → Teilgewinn mitnehmen (mind. 50 %) oder Stop nachziehen.")
        elif pnl_pct < -15:
            recs.append(f"**{name}** ({t}): {pnl_pct:.1f} %. Katalysator noch intakt? Sonst schließen.")
        else:
            recs.append(f"**{name}** ({t}): {pnl_pct:+.1f} %. → Halten, Momentum/Katalysator weiter beobachten.")

    return recs


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Portfolio-Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS für moderneres Aussehen
st.markdown("""
<style>
    .main-header {font-size: 1.8rem; font-weight: 700; margin-bottom: 0.2rem;}
    .sub-header {color: #666; font-size: 0.95rem; margin-bottom: 1.5rem;}
    .metric-card {background: #f8f9fa; border-radius: 10px; padding: 1rem; border: 1px solid #e9ecef;}
    .stButton>button {border-radius: 8px; font-weight: 600;}
    div[data-testid="stMetricValue"] {font-size: 1.4rem;}
</style>
""", unsafe_allow_html=True)

if "data" not in st.session_state:
    st.session_state.data = load_data()
data = st.session_state.data

# ----- Internet Status -----
internet_ok = check_internet()
status_col1, status_col2 = st.columns([4, 1])
with status_col1:
    if internet_ok:
        st.success("✅ Internetverbindung aktiv – Live-Kurse & News verfügbar")
    else:
        st.error("🚨 KEINE Internetverbindung – Empfehlungen sind deaktiviert. Es werden keine gespeicherten oder erfundenen Empfehlungen ausgegeben.")
with status_col2:
    st.caption(datetime.now().strftime("%d.%m.%Y %H:%M"))

st.markdown('<p class="main-header">Portfolio-Agent</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Topf A = langfristiger Vermögensaufbau · Topf B = begrenztes Trading-Budget</p>', unsafe_allow_html=True)

# ----- Sidebar -----
with st.sidebar:
    st.header("Einstellungen")
    st.subheader("Topf A")
    data["topf_a"]["risk_level"] = st.selectbox(
        "Risikolevel",
        ["Konservativ", "Wachstum", "Dynamisch"],
        index=["Konservativ", "Wachstum", "Dynamisch"].index(data["topf_a"].get("risk_level", "Wachstum"))
    )
    data["topf_a"]["horizon"] = st.selectbox(
        "Horizont",
        ["5–7 Jahre", "10+ Jahre", "15+ Jahre"],
        index=["5–7 Jahre", "10+ Jahre", "15+ Jahre"].index(data["topf_a"].get("horizon", "10+ Jahre"))
    )
    data["topf_a"]["startkapital"] = st.number_input(
        "Startkapital (CHF)", min_value=1000.0,
        value=float(data["topf_a"].get("startkapital", 10000.0)), step=500.0
    )

    st.subheader("Topf B")
    data["topf_b"]["risk_level"] = st.selectbox(
        "Risikolevel",
        ["Sehr strikt", "Strikt begrenzt", "Moderat"],
        index=["Sehr strikt", "Strikt begrenzt", "Moderat"].index(data["topf_b"].get("risk_level", "Strikt begrenzt"))
    )
    data["topf_b"]["horizon"] = st.selectbox(
        "Horizont",
        ["Sehr kurz (Tage)", "Kurz (Tage–Monate)", "Bis 3 Monate"],
        index=["Sehr kurz (Tage)", "Kurz (Tage–Monate)", "Bis 3 Monate"].index(data["topf_b"].get("horizon", "Kurz (Tage–Monate)"))
    )
    data["topf_b"]["max_verlustbudget"] = st.number_input(
        "Max. Verlustbudget (CHF)", min_value=100.0,
        value=float(data["topf_b"].get("max_verlustbudget", 1000.0)), step=100.0
    )

    st.divider()
    st.subheader("Position hinzufügen")

    topf_sel = st.radio("Topf wählen", ["Topf A", "Topf B"], horizontal=True)
    topf_key = "topf_a" if topf_sel == "Topf A" else "topf_b"

    opts = instrument_options("A" if topf_sel == "Topf A" else "B")
    if not opts:
        st.warning("Keine Instrumente für diesen Topf definiert.")
    else:
        selected_label = st.selectbox("Instrument aus Liste wählen", list(opts.keys()))
        selected_ticker = opts[selected_label]
        meta = INSTRUMENTS[selected_ticker]

        st.caption(f"{meta['desc']} · {meta['type'].upper()} · {meta['currency']}")

        # Live-Preis laden
        live_price = None
        if internet_ok and selected_ticker != "CASH.CHF":
            with st.spinner("Aktueller Preis wird geladen..."):
                info = get_price_info(selected_ticker)
                if info:
                    live_price = info["price"]
                    st.info(f"Aktueller Kurs: **{live_price:.2f} {info.get('currency', '')}**  ({info.get('change_pct', 0):+.2f} %)")
                else:
                    st.warning("Kurs konnte nicht geladen werden.")
        elif selected_ticker == "CASH.CHF":
            live_price = 1.0
            st.info("Bargeld wird 1:1 in CHF geführt.")

        shares = st.number_input(
            "Stückzahl / Betrag" if selected_ticker != "CASH.CHF" else "Betrag in CHF",
            min_value=0.01, value=1.0, step=0.1
        )

        # Durchschnittspreis: bei Live-Preis vorausfüllen, sonst manuell
        default_price = live_price if live_price else 100.0
        avg_price = st.number_input(
            "Einstandspreis (wird mit Live-Kurs vorausgefüllt)",
            min_value=0.01, value=float(default_price), step=0.01,
            help="Du kannst den Preis anpassen, falls dein echter Einstand abweicht."
        )

        stop_loss = None
        if topf_sel == "Topf B" and selected_ticker != "CASH.CHF":
            suggested_stop = avg_price * 0.92  # ca. -8 %
            stop_loss = st.number_input("Stop-Loss (Pflicht)", min_value=0.01, value=float(suggested_stop), step=0.01)

        if st.button("Position speichern", type="primary", use_container_width=True):
            if topf_key == "topf_b" and len(data["topf_b"]["holdings"]) >= data["topf_b"].get("max_positionen", 4):
                st.error("Maximale Anzahl Positionen in Topf B erreicht (4).")
            else:
                entry = {
                    "shares": float(shares),
                    "avg_price": float(avg_price),
                    "name": meta["name"],
                    "type": meta["type"],
                    "entry_date": datetime.now().strftime("%Y-%m-%d")
                }
                if stop_loss is not None:
                    entry["stop_loss"] = float(stop_loss)
                data[topf_key]["holdings"][selected_ticker] = entry
                save_data(data)
                st.session_state.data = data
                st.success(f"{meta['name']} wurde in {topf_sel} gespeichert.")
                st.rerun()

    st.divider()
    if st.button("Alle Einstellungen speichern", use_container_width=True):
        save_data(data)
        st.session_state.data = data
        st.success("Gespeichert.")

# ----- Hauptbereich -----
tab_a, tab_b, tab_rules = st.tabs(["Topf A – Anlage", "Topf B – Trading", "Risiko-Regeln"])

# ==================== TOPF A ====================
with tab_a:
    st.subheader("Topf A – Langfristiger Vermögensaufbau")
    c1, c2, c3 = st.columns(3)
    c1.metric("Risikolevel", data["topf_a"]["risk_level"])
    c2.metric("Horizont", data["topf_a"]["horizon"])
    c3.metric("Startkapital", f"{data['topf_a']['startkapital']:,.0f} CHF")

    holdings_a = data["topf_a"]["holdings"]
    prices_a = {}

    if holdings_a and internet_ok:
        with st.spinner("Kurse werden aktualisiert..."):
            for t in list(holdings_a.keys()):
                info = get_price_info(t)
                if info:
                    prices_a[t] = info["price"]
                    holdings_a[t]["name"] = info.get("name", holdings_a[t].get("name", t))
                    holdings_a[t]["_change"] = info.get("change_pct", 0.0)
                    holdings_a[t]["_currency"] = info.get("currency", "")
                else:
                    prices_a[t] = holdings_a[t].get("avg_price", 0)
    else:
        for t, h in holdings_a.items():
            prices_a[t] = h.get("avg_price", 0)

    if not holdings_a:
        st.info("Topf A ist noch leer. Wähle links in der Sidebar Instrumente aus der vordefinierten Liste.")
    else:
        rows = []
        total = 0.0
        for t, h in holdings_a.items():
            val = h["shares"] * prices_a.get(t, h["avg_price"])
            total += val
            rows.append({
                "Instrument": h.get("name", t),
                "Ticker": t,
                "Stück / Betrag": h["shares"],
                "Einstand": round(h["avg_price"], 2),
                "Aktuell": round(prices_a.get(t, 0), 2),
                "Wert": round(val, 2),
                "Δ %": round(h.get("_change", 0), 2)
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.metric("Aktueller Gesamtwert (ca.)", f"{total:,.2f}")

    # Update & Empfehlungen
    if st.button("Update & Empfehlungen Topf A", type="primary", disabled=not internet_ok, key="upd_a"):
        if not internet_ok:
            st.error("Keine Internetverbindung – es werden keine Empfehlungen ausgegeben.")
        else:
            total_val = calc_portfolio_value(holdings_a, prices_a)
            recs = generate_recommendations_a(holdings_a, prices_a, total_val, internet_ok)
            st.markdown("### Handlungsempfehlungen")
            for r in recs:
                st.markdown(f"- {r}")

            if holdings_a:
                st.markdown("### Aktuelle News")
                for t in holdings_a:
                    if t == "CASH.CHF":
                        continue
                    news = get_news(t)
                    if news:
                        st.write(f"**{INSTRUMENTS.get(t, {}).get('name', t)}**")
                        for n in news:
                            st.markdown(f"- [{n['title']}]({n['link']})  · {n['published']}")

# ==================== TOPF B ====================
with tab_b:
    st.subheader("Topf B – Trading mit klarem Verlustbudget")
    budget = data["topf_b"]["max_verlustbudget"]
    real_loss = data["topf_b"].get("realisierter_verlust", 0.0)
    remaining = max(0.0, budget - real_loss)

    c1, c2, c3 = st.columns(3)
    c1.metric("Max. Verlustbudget", f"{budget:,.0f} CHF")
    c2.metric("Bereits realisiert", f"{real_loss:,.0f} CHF")
    c3.metric("Noch verfügbar", f"{remaining:,.0f} CHF")

    if remaining <= 0:
        st.error("Verlustbudget ausgeschöpft – keine neuen Trades erlaubt.")

    holdings_b = data["topf_b"]["holdings"]
    prices_b = {}
    open_risk = 0.0

    if holdings_b and internet_ok:
        with st.spinner("Kurse Topf B werden geladen..."):
            for t in list(holdings_b.keys()):
                info = get_price_info(t)
                if info:
                    prices_b[t] = info["price"]
                    holdings_b[t]["name"] = info.get("name", holdings_b[t].get("name", t))
                    holdings_b[t]["_change"] = info.get("change_pct", 0.0)
                else:
                    prices_b[t] = holdings_b[t].get("avg_price", 0)
    else:
        for t, h in holdings_b.items():
            prices_b[t] = h.get("avg_price", 0)

    if not holdings_b:
        st.info("Topf B ist leer. Nur Positionen mit Katalysator oder klarem Momentum eintragen.")
    else:
        rows = []
        for t, h in holdings_b.items():
            price = prices_b.get(t, h["avg_price"])
            val = h["shares"] * price
            stop = h.get("stop_loss")
            risk = 0.0
            if stop:
                risk = h["shares"] * abs(price - stop)
                open_risk += risk
            rows.append({
                "Instrument": h.get("name", t),
                "Ticker": t,
                "Stück": h["shares"],
                "Einstand": round(h["avg_price"], 2),
                "Aktuell": round(price, 2),
                "Stop-Loss": stop,
                "Risiko (ca.)": round(risk, 2),
                "Wert": round(val, 2),
                "Δ %": round(h.get("_change", 0), 2)
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.metric("Geschätztes offenes Risiko", f"{open_risk:,.2f} CHF")

    if st.button("Update & Empfehlungen Topf B", type="primary", disabled=not internet_ok, key="upd_b"):
        if not internet_ok:
            st.error("Keine Internetverbindung – es werden keine Empfehlungen ausgegeben.")
        else:
            recs = generate_recommendations_b(holdings_b, prices_b, remaining, open_risk, internet_ok)
            st.markdown("### Handlungsempfehlungen")
            for r in recs:
                st.markdown(f"- {r}")

            if holdings_b:
                st.markdown("### News zu den Positionen")
                for t in holdings_b:
                    if t == "CASH.CHF":
                        continue
                    news = get_news(t)
                    if news:
                        st.write(f"**{INSTRUMENTS.get(t, {}).get('name', t)}**")
                        for n in news:
                            st.markdown(f"- [{n['title']}]({n['link']})  · {n['published']}")

# ==================== REGELN ====================
with tab_rules:
    st.subheader("Verbindliche Risiko-Regeln")
    st.markdown("""
**Topf A – Langfristig (10+ Jahre)**  
- Breite Streuung über globale ETFs  
- Nur Instrumente aus der vordefinierten Liste  
- Rebalancing bei Abweichung > 6 % vom Zielgewicht  
- Kleiner Gold-Anteil (ca. 5 %) als Absicherung möglich  
- Keine Hebel, keine Derivate  
- Bei starken Drawdowns: halten, nicht verkaufen  

**Topf B – Trading**  
- Hartes Verlustbudget (aktuell 1’000 CHF) – wird nie überschritten  
- Maximal 4 offene Positionen  
- Pro Trade max. ca. 20–25 % des noch verfügbaren Budgets riskieren  
- Stop-Loss bei jedem Trade Pflicht  
- Nur handeln bei Katalysator oder klarem Momentum  
- Gewinne teilweise mitnehmen ab ca. +35 %  

**Übergreifend**  
- Empfehlungen nur bei aktiver Internetverbindung  
- Nur vordefinierte Instrumente (keine Fantasie-Ticker)  
- Strikte Trennung der beiden Töpfe  
- Du entscheidest immer selbst
""")

st.divider()
st.caption("Portfolio-Agent v2.0 · Nur Entscheidungsunterstützung · Keine Anlageberatung")
