# =========================================================
# 🍻 OST UNIVERSE
# Display symbol = what you see
# Data symbol(s) = what Yahoo/yfinance tries to download
# =========================================================

OST_UNIVERSE = {

    "ABCL": {
        "data_symbol": "ABCL",
        "sector": "Biotech",
        "liquidity": 2,
        "volatility": 5,
        "regime": ["speculative_growth"],
    },

    "ATH": {
        "data_symbol": "ATH.TO",
        "data_symbols": ["ATH.TO", "ATH"],
        "sector": "Energy",
        "liquidity": 4,
        "volatility": 4,
        "regime": ["oil_beta", "small_mid_cap"],
    },

    "COST": {
        "data_symbol": "COST",
        "sector": "Consumer Defensive",
        "liquidity": 5,
        "volatility": 2,
        "regime": ["defensive", "blue_chip"],
    },

    "JUGR": {
        "data_symbol": "JUGR.V",
        "data_symbols": ["JUGR.V", "JUGR"],
        "sector": "Speculative",
        "liquidity": 1,
        "volatility": 5,
        "regime": ["micro_cap", "high_risk"],
    },

    "KFR": {
        "data_symbol": "KFR.V",
        "data_symbols": ["KFR.V", "KFR"],
        "sector": "Energy",
        "liquidity": 2,
        "volatility": 4,
        "regime": ["commodity_beta"],
    },

    "FLTCF": {
        "data_symbol": "FLTCF",
        "sector": "Mining",
        "liquidity": 1,
        "volatility": 5,
        "regime": ["micro_cap", "commodity_beta"],
    },

    "FTDR": {
        "data_symbol": "FTDR",
        "sector": "Technology",
        "liquidity": 3,
        "volatility": 4,
        "regime": ["growth", "mid_cap"],
    },

    "FUTU": {
        "data_symbol": "FUTU",
        "sector": "Financial",
        "liquidity": 4,
        "volatility": 5,
        "regime": ["china_beta", "high_momentum"],
    },

    "GLW": {
        "data_symbol": "GLW",
        "sector": "Industrials",
        "liquidity": 4,
        "volatility": 3,
        "regime": ["cyclical", "value"],
    },

    "MSFT": {
        "data_symbol": "MSFT",
        "sector": "Technology",
        "liquidity": 5,
        "volatility": 2,
        "regime": ["mega_cap", "quality", "ai_leader"],
    },

    # -----------------------------------------------------
    # PHOS is problematic on Yahoo.
    # Use fallback candidates so scanner survives symbol
    # inconsistencies and OTC/CSE feed changes.
    # -----------------------------------------------------

    "PHOS": {
        "data_symbol": "PHOS.CN",
        "data_symbols": [
            "PHOS.CN",
            "PHOS",
            "PHOSF",
        ],
        "sector": "Materials",
        "liquidity": 1,
        "volatility": 5,
        "regime": ["speculative", "commodity_beta"],
    },

    "SCR": {
        "data_symbol": "SCR.TO",
        "data_symbols": ["SCR.TO", "SCR"],
        "sector": "Energy",
        "liquidity": 4,
        "volatility": 4,
        "regime": ["oil_beta", "canada_energy"],
    },

    "XOM": {
        "data_symbol": "XOM",
        "sector": "Energy",
        "liquidity": 5,
        "volatility": 3,
        "regime": ["oil_major", "commodity_beta"],
    },
}