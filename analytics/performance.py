# =========================================================
# 📊 JFBP PERFORMANCE ANALYTICS v28.1
# LIVE JOURNAL / PORTFOLIO ANALYTICS FIX
#
# Fixes:
#   - realized_delta is used for per-trade win/loss analytics
#   - realized_pnl is treated as cumulative if present
#   - breakeven trades handled cleanly
#   - best/worst trade now work correctly
#   - symbol and daily analytics receive correct P&L field
# =========================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List
import pandas as pd


@dataclass
class PerformanceReport:

    total_trades: int

    winners: int
    losers: int
    breakeven: int

    win_rate: float
    loss_rate: float

    avg_win: float
    avg_loss: float

    profit_factor: float
    expectancy: float

    best_trade: float
    worst_trade: float

    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float

    gross_exposure: float
    long_exposure: float
    short_exposure: float
    net_exposure: float

    long_positions: int
    short_positions: int


class PerformanceAnalyzer:

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            return float(value)
        except Exception:
            return 0.0

    @staticmethod
    def _ledger_df(ledger: List[Dict[str, Any]]) -> pd.DataFrame:
        if not ledger:
            return pd.DataFrame([])

        try:
            return pd.DataFrame(ledger)
        except Exception:
            return pd.DataFrame([])

    @staticmethod
    def trade_pnl_series(trades_df: pd.DataFrame) -> pd.Series:
        """
        Per-trade P&L source of truth.

        Use realized_delta first because portfolio ledger stores
        each trade's incremental realized P&L there.

        realized_pnl may be cumulative after a symbol's full history,
        so it should not be used for win/loss classification unless
        realized_delta does not exist.
        """

        if trades_df.empty:
            return pd.Series(dtype=float)

        if "realized_delta" in trades_df.columns:
            return pd.to_numeric(
                trades_df["realized_delta"],
                errors="coerce",
            ).fillna(0.0)

        if "pnl" in trades_df.columns:
            return pd.to_numeric(
                trades_df["pnl"],
                errors="coerce",
            ).fillna(0.0)

        if "realized_pnl" in trades_df.columns:
            return pd.to_numeric(
                trades_df["realized_pnl"],
                errors="coerce",
            ).fillna(0.0)

        return pd.Series(dtype=float)

    def analyze(
        self,
        ledger: List[Dict[str, Any]],
        positions_snapshot: Dict[str, Dict[str, Any]],
        exposure_snapshot: Dict[str, Any],
    ) -> PerformanceReport:

        trades_df = self._ledger_df(ledger)
        trade_pnl = self.trade_pnl_series(trades_df)

        total_trades = int(len(trade_pnl))

        winners = int((trade_pnl > 0).sum())
        losers = int((trade_pnl < 0).sum())
        breakeven = int((trade_pnl == 0).sum())

        win_rate = winners / total_trades if total_trades else 0.0
        loss_rate = losers / total_trades if total_trades else 0.0

        winning_trades = trade_pnl[trade_pnl > 0]
        losing_trades = trade_pnl[trade_pnl < 0]

        avg_win = float(winning_trades.mean()) if not winning_trades.empty else 0.0
        avg_loss = float(losing_trades.mean()) if not losing_trades.empty else 0.0

        gross_profit = float(winning_trades.sum()) if not winning_trades.empty else 0.0
        gross_loss = abs(float(losing_trades.sum())) if not losing_trades.empty else 0.0

        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

        expectancy = (
            (win_rate * avg_win)
            - (loss_rate * abs(avg_loss))
        )

        best_trade = float(trade_pnl.max()) if not trade_pnl.empty else 0.0
        worst_trade = float(trade_pnl.min()) if not trade_pnl.empty else 0.0

        realized_pnl = self._safe_float(
            exposure_snapshot.get("realized_pnl", 0.0)
        )

        unrealized_pnl = self._safe_float(
            exposure_snapshot.get("unrealized_pnl", 0.0)
        )

        total_pnl = self._safe_float(
            exposure_snapshot.get("total_pnl", realized_pnl + unrealized_pnl)
        )

        gross_exposure = self._safe_float(
            exposure_snapshot.get("gross_exposure", 0.0)
        )

        long_exposure = self._safe_float(
            exposure_snapshot.get("long_exposure", 0.0)
        )

        short_exposure = self._safe_float(
            exposure_snapshot.get("short_exposure", 0.0)
        )

        net_exposure = self._safe_float(
            exposure_snapshot.get("net_exposure", 0.0)
        )

        long_positions = 0
        short_positions = 0

        for pos in positions_snapshot.values():
            side = str(pos.get("side", "FLAT")).upper()

            if side == "LONG":
                long_positions += 1
            elif side == "SHORT":
                short_positions += 1

        return PerformanceReport(
            total_trades=total_trades,

            winners=winners,
            losers=losers,
            breakeven=breakeven,

            win_rate=win_rate,
            loss_rate=loss_rate,

            avg_win=avg_win,
            avg_loss=avg_loss,

            profit_factor=profit_factor,
            expectancy=expectancy,

            best_trade=best_trade,
            worst_trade=worst_trade,

            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            total_pnl=total_pnl,

            gross_exposure=gross_exposure,
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            net_exposure=net_exposure,

            long_positions=long_positions,
            short_positions=short_positions,
        )

    @staticmethod
    def report_to_dict(report: PerformanceReport) -> Dict[str, Any]:

        return {
            "Total Trades": report.total_trades,
            "Winners": report.winners,
            "Losers": report.losers,
            "Breakeven": report.breakeven,

            "Win Rate": report.win_rate,
            "Loss Rate": report.loss_rate,

            "Average Win": report.avg_win,
            "Average Loss": report.avg_loss,

            "Profit Factor": report.profit_factor,
            "Expectancy": report.expectancy,

            "Best Trade": report.best_trade,
            "Worst Trade": report.worst_trade,

            "Realized P&L": report.realized_pnl,
            "Unrealized P&L": report.unrealized_pnl,
            "Total P&L": report.total_pnl,

            "Gross Exposure": report.gross_exposure,
            "Long Exposure": report.long_exposure,
            "Short Exposure": report.short_exposure,
            "Net Exposure": report.net_exposure,

            "Long Positions": report.long_positions,
            "Short Positions": report.short_positions,
        }