# =========================================================
# 🌍 JFBP MASTER TRADING UNIVERSE
# =========================================================

JFBP_UNIVERSE = {
    # =========================
    # ETFs / Market Engines
    # =========================
    "SPY":  {"sector": "ETF", "liquidity": 5, "volatility": 3, "regime": ["broad_market"]},
    "QQQ":  {"sector": "ETF", "liquidity": 5, "volatility": 4, "regime": ["tech_beta", "risk_on"]},
    "IWM":  {"sector": "ETF", "liquidity": 4, "volatility": 4, "regime": ["small_cap", "risk_sentiment"]},
    "DIA":  {"sector": "ETF", "liquidity": 4, "volatility": 2, "regime": ["blue_chip"]},
    "TQQQ": {"sector": "ETF", "liquidity": 4, "volatility": 5, "regime": ["leveraged_momentum"]},
    "UVXY": {"sector": "ETF", "liquidity": 4, "volatility": 5, "regime": ["volatility", "risk_off"]},

    # =========================
    # Mega Cap Tech
    # =========================
    "AAPL": {"sector": "Tech", "liquidity": 5, "volatility": 2, "regime": ["defensive_growth"]},
    "MSFT": {"sector": "Tech", "liquidity": 5, "volatility": 2, "regime": ["cloud", "quality"]},
    "NVDA": {"sector": "Tech", "liquidity": 5, "volatility": 5, "regime": ["ai", "momentum", "risk_on"]},
    "AMZN": {"sector": "Tech", "liquidity": 5, "volatility": 3, "regime": ["growth"]},
    "GOOGL": {"sector": "Tech", "liquidity": 5, "volatility": 3, "regime": ["search", "ai"]},
    "META": {"sector": "Tech", "liquidity": 5, "volatility": 4, "regime": ["ads", "momentum"]},
    "TSLA": {"sector": "Tech", "liquidity": 5, "volatility": 5, "regime": ["high_beta", "risk_on"]},
    "AVGO": {"sector": "Tech", "liquidity": 4, "volatility": 3, "regime": ["semis", "quality"]},
    "AMD": {"sector": "Tech", "liquidity": 5, "volatility": 5, "regime": ["semis", "momentum"]},
    "ORCL": {"sector": "Tech", "liquidity": 4, "volatility": 3, "regime": ["enterprise", "cloud"]},

    # =========================
    # Semiconductors / AI Infra
    # =========================
    "SMCI": {"sector": "Semis", "liquidity": 4, "volatility": 5, "regime": ["ai_infra", "momentum"]},
    "MU": {"sector": "Semis", "liquidity": 4, "volatility": 4, "regime": ["cyclical", "memory"]},
    "LRCX": {"sector": "Semis", "liquidity": 4, "volatility": 4, "regime": ["equipment"]},
    "KLAC": {"sector": "Semis", "liquidity": 4, "volatility": 3, "regime": ["equipment", "quality"]},
    "AMAT": {"sector": "Semis", "liquidity": 4, "volatility": 3, "regime": ["equipment"]},
    "ASML": {"sector": "Semis", "liquidity": 4, "volatility": 3, "regime": ["eu_semis", "quality"]},
    "ARM": {"sector": "Semis", "liquidity": 4, "volatility": 4, "regime": ["ip", "ai"]},
    "INTC": {"sector": "Semis", "liquidity": 4, "volatility": 3, "regime": ["turnaround"]},
    "TSM": {"sector": "Semis", "liquidity": 5, "volatility": 3, "regime": ["foundry", "ai"]},

    # =========================
    # Financials
    # =========================
    "JPM": {"sector": "Financials", "liquidity": 5, "volatility": 3, "regime": ["rates", "banking"]},
    "BAC": {"sector": "Financials", "liquidity": 5, "volatility": 4, "regime": ["rates", "cyclical"]},
    "GS": {"sector": "Financials", "liquidity": 4, "volatility": 4, "regime": ["markets", "trading"]},
    "MS": {"sector": "Financials", "liquidity": 4, "volatility": 3, "regime": ["wealth", "markets"]},
    "WFC": {"sector": "Financials", "liquidity": 4, "volatility": 3, "regime": ["rates"]},
    "V": {"sector": "Financials", "liquidity": 5, "volatility": 2, "regime": ["payments", "defensive"]},
    "MA": {"sector": "Financials", "liquidity": 5, "volatility": 2, "regime": ["payments"]},
    "BX": {"sector": "Financials", "liquidity": 4, "volatility": 4, "regime": ["alternatives", "rates"]},
    "COIN": {"sector": "Financials", "liquidity": 4, "volatility": 5, "regime": ["crypto_beta", "risk_on"]},

    # =========================
    # Energy
    # =========================
    "XOM": {"sector": "Energy", "liquidity": 5, "volatility": 3, "regime": ["inflation", "oil"]},
    "CVX": {"sector": "Energy", "liquidity": 5, "volatility": 3, "regime": ["oil"]},
    "COP": {"sector": "Energy", "liquidity": 4, "volatility": 4, "regime": ["cyclical"]},
    "OXY": {"sector": "Energy", "liquidity": 4, "volatility": 5, "regime": ["high_beta_oil"]},
    "SLB": {"sector": "Energy", "liquidity": 4, "volatility": 4, "regime": ["services", "cyclical"]},

    # =========================
    # Industrials
    # =========================
    "CAT": {"sector": "Industrials", "liquidity": 4, "volatility": 3, "regime": ["cyclical", "macro"]},
    "DE": {"sector": "Industrials", "liquidity": 4, "volatility": 3, "regime": ["agriculture"]},
    "BA": {"sector": "Industrials", "liquidity": 4, "volatility": 4, "regime": ["recovery", "cyclical"]},
    "GE": {"sector": "Industrials", "liquidity": 4, "volatility": 3, "regime": ["industrial_restructuring"]},
    "HON": {"sector": "Industrials", "liquidity": 4, "volatility": 2, "regime": ["quality"]},

    # =========================
    # Consumer Defensive
    # =========================
    "WMT": {"sector": "Consumer", "liquidity": 5, "volatility": 2, "regime": ["defensive", "inflation"]},
    "COST": {"sector": "Consumer", "liquidity": 5, "volatility": 3, "regime": ["quality"]},
    "PG": {"sector": "Consumer", "liquidity": 5, "volatility": 1, "regime": ["defensive"]},
    "KO": {"sector": "Consumer", "liquidity": 5, "volatility": 1, "regime": ["defensive"]},
    "MCD": {"sector": "Consumer", "liquidity": 5, "volatility": 2, "regime": ["defensive", "global"]},
    "NKE": {"sector": "Consumer", "liquidity": 4, "volatility": 3, "regime": ["growth", "brand"]},
}