"""
Strategy Registry

Contains metadata only.

No calculations belong here.
"""

STRATEGY_REGISTRY = {

    "Cash-Secured Put": {

        "id": "cash_secured_put",

        "name": "Cash-Secured Put",

        "category": "Income",

        "defined_risk": True,

        "requires_shares": False,

        "requires_cash": True,

        "capital_requirement":
            "Cash to purchase 100 shares if assigned.",

        "primary_objective":
            "Generate premium while potentially acquiring stock.",

        "description":
            "Sell a put while holding sufficient cash to buy shares."
    },

    "Covered Call": {

        "id": "covered_call",

        "name": "Covered Call",

        "category": "Income",

        "defined_risk": False,

        "requires_shares": True,

        "requires_cash": False,

        "capital_requirement":
            "Own at least 100 shares.",

        "primary_objective":
            "Generate income from existing shares.",

        "description":
            "Sell call options against owned shares."
    },

    "Bull Put Spread": {

        "id": "bull_put_spread",

        "name": "Bull Put Spread",

        "category": "Bullish",

        "defined_risk": True,

        "requires_shares": False,

        "requires_cash": False,

        "capital_requirement":
            "Spread width minus collected credit.",

        "primary_objective":
            "Generate bullish premium with limited downside.",

        "description":
            "Short put protected by a lower strike long put."
    },

    "Bull Call Spread": {

        "id": "bull_call_spread",

        "name": "Bull Call Spread",

        "category": "Bullish",

        "defined_risk": True,

        "requires_shares": False,

        "requires_cash": False,

        "capital_requirement":
            "Net debit paid.",

        "primary_objective":
            "Participate in upside while limiting risk.",

        "description":
            "Long call financed by a higher strike short call."
    }

}