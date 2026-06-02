from dataclasses import dataclass
from typing import Dict, List, Optional

import time

from data.market_cache import MarketCache


# =========================================================
# 🧠 SIGNAL SCORE MODEL
# =========================================================

@dataclass
class SignalScore:
    ticker: str
    liquidity_score: float
    volatility_score: float
    trend_score: float
    volume_score: float
    regime_score: float
    composite_score: float


# =========================================================
# 🧠 QUANT BRAIN ENGINE (CACHE-DRIVEN v3)
# =========================================================

class QuantBrain:

    def __init__(self, universe: Dict[str, dict]):

        self.universe = universe

        # ⚡ LIVE MARKET CACHE (single source of truth)
        self.cache = MarketCache(ttl=10)


    # =====================================================
    # 🧠 FEATURE ACCESS LAYER (FAST + CACHED)
    # =====================================================

    def _get_features(self, ticker: str):

        df = self.cache.get(ticker)

        if df is None or df.empty:
            return None

        return df.iloc[-1].to_dict()


    # =====================================================
    # 📊 BASE SCORES
    # =====================================================

    def liquidity_score(self, ticker: str) -> float:
        return self.universe[ticker]["liquidity"]

    def volatility_score(self, ticker: str) -> float:
        return self.universe[ticker]["volatility"]

    def regime_score(self, ticker: str, active_regimes: List[str]) -> float:

        tags = self.universe[ticker]["regime"]
        return sum(1 for r in tags if r in active_regimes)


    # =====================================================
    # 📈 TREND SCORE (REAL SIGNALS)
    # =====================================================

    def trend_score(self, ticker: str) -> float:

        row = self._get_features(ticker)
        if row is None:
            return 0.0

        ema_slope = row.get("EMA_SLOPE", 0.0)
        macd = row.get("MACD", 0.0)
        breakout = row.get("BREAKOUT", 0.0)

        return float(
            0.4 * ema_slope +
            0.4 * macd +
            0.2 * breakout
        )


    # =====================================================
    # 📊 VOLUME / MOMENTUM SCORE
    # =====================================================

    def volume_score(self, ticker: str) -> float:

        row = self._get_features(ticker)
        if row is None:
            return 0.0

        vol_spike = row.get("VOLUME_SPIKE", 0.0)
        vol_ratio = row.get("Volume_Ratio", 1.0)
        rsi_signal = row.get("RSI_SIGNAL", 0.0)

        return float(
            0.5 * vol_spike +
            0.3 * min(vol_ratio / 2.0, 1.0) +
            0.2 * rsi_signal
        )


    # =====================================================
    # 🧠 COMPOSITE SCORE ENGINE
    # =====================================================

    def composite_score(self, ticker: str, active_regimes: List[str]):

        liq = self.liquidity_score(ticker)
        vol = self.volatility_score(ticker)
        reg = self.regime_score(ticker, active_regimes)

        trend = self.trend_score(ticker)
        volume = self.volume_score(ticker)

        score = (
            0.25 * liq +
            0.20 * vol +
            0.25 * trend +
            0.15 * volume +
            0.15 * reg
        )

        return SignalScore(
            ticker=ticker,
            liquidity_score=liq,
            volatility_score=vol,
            trend_score=trend,
            volume_score=volume,
            regime_score=reg,
            composite_score=float(score)
        )


    # =====================================================
    # 🏆 RANKING ENGINE
    # =====================================================

    def rank_universe(self, active_regimes: List[str]) -> List[SignalScore]:

        scores = [
            self.composite_score(ticker, active_regimes)
            for ticker in self.universe.keys()
        ]

        return sorted(scores, key=lambda x: x.composite_score, reverse=True)


    # =====================================================
    # 🚦 TRADE FILTER
    # =====================================================

    def tradable_set(
        self,
        active_regimes: List[str],
        min_score: float = 1.5
    ) -> List[str]:

        ranked = self.rank_universe(active_regimes)

        return [
            r.ticker
            for r in ranked
            if r.composite_score >= min_score
        ]