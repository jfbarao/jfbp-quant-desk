# =========================================================
# 🧠 JFBP QUANT DESK v15 — AI COMMENTATOR
# =========================================================

from __future__ import annotations

from typing import Dict, Any, Optional


class AICommentator:

    def generate(self, data: Dict[str, Any]) -> str:

        ticker = str(data.get("ticker", "")).upper()
        trend = str(data.get("trend", "")).upper()
        signal = str(data.get("signal", "")).upper()

        rs_score = data.get("rsi", None)
        support = data.get("support", None)
        resistance = data.get("resistance", None)

        commentary = []

        # =================================================
        # TREND ANALYSIS
        # =================================================

        if trend == "BULLISH":
            commentary.append(
                f"{ticker} remains in a constructive bullish trend."
            )

        elif trend == "BEARISH":
            commentary.append(
                f"{ticker} remains under bearish pressure."
            )

        else:
            commentary.append(
                f"{ticker} has a neutral or unclear trend profile."
            )

        # =================================================
        # RELATIVE STRENGTH / MOMENTUM LOGIC
        # =================================================

        try:
            rs_score = float(rs_score)
        except Exception:
            rs_score = None

        if rs_score is not None:

            if rs_score >= 1.05:
                commentary.append(
                    "Relative strength is strong versus the benchmark."
                )

            elif rs_score <= 0.97:
                commentary.append(
                    "Relative strength is weak versus the benchmark."
                )

            else:
                commentary.append(
                    "Relative strength remains neutral to constructive."
                )

        # =================================================
        # SUPPORT / RESISTANCE
        # =================================================

        support_text = self._format_price(support)
        resistance_text = self._format_price(resistance)

        if support_text:
            commentary.append(
                f"Key support is near {support_text}."
            )

        if resistance_text:
            commentary.append(
                f"Resistance is located near {resistance_text}."
            )

        # =================================================
        # SIGNAL LOGIC
        # =================================================

        if signal == "BUY":
            commentary.append(
                "Current conditions favor bullish continuation setups."
            )

        elif signal == "SELL":
            commentary.append(
                "Risk management remains important as downside pressure persists."
            )

        elif signal == "NO TRADE":
            commentary.append(
                "No trade setup is active at this time."
            )

        return " ".join(commentary)

    def _format_price(self, value: Optional[float]) -> str:

        try:
            value = float(value)
        except Exception:
            return ""

        if value <= 0:
            return ""

        return f"${value:.2f}"