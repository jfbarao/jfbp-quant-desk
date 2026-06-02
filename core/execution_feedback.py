from dataclasses import dataclass
from typing import Dict, List, Optional


# =========================================================
# 📊 TRADE RESULT MODEL
# =========================================================

@dataclass
class TradeResult:
    symbol: str
    side: str
    qty: float
    entry_price: float
    exit_price: Optional[float] = None
    pnl: float = 0.0
    slippage: float = 0.0
    strategy_score: float = 0.0


# =========================================================
# 🔁 FEEDBACK ENGINE
# =========================================================

class ExecutionFeedback:

    def __init__(self):

        # stores completed trades
        self.trades: List[TradeResult] = []

        # rolling performance metrics
        self.total_pnl = 0.0
        self.win_rate = 0.0


    # =====================================================
    # 📥 RECORD TRADE ENTRY
    # =====================================================

    def record_entry(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        strategy_score: float
    ):

        trade = TradeResult(
            symbol=symbol,
            side=side,
            qty=qty,
            entry_price=price,
            strategy_score=strategy_score
        )

        self.trades.append(trade)


    # =====================================================
    # 📤 CLOSE TRADE
    # =====================================================

    def close_trade(
        self,
        symbol: str,
        exit_price: float
    ):

        for trade in reversed(self.trades):

            if trade.symbol == symbol and trade.exit_price is None:

                trade.exit_price = exit_price

                # -------------------------
                # PnL CALCULATION
                # -------------------------

                direction = 1 if trade.side == "BUY" else -1

                trade.pnl = (
                    direction * (exit_price - trade.entry_price) * trade.qty
                )

                # -------------------------
                # SLIPPAGE (simplified model)
                # -------------------------

                trade.slippage = abs(exit_price - trade.entry_price) * 0.001

                self.total_pnl += trade.pnl

                break


    # =====================================================
    # 📊 PERFORMANCE METRICS
    # =====================================================

    def get_stats(self) -> Dict:

        closed = [t for t in self.trades if t.exit_price is not None]

        if not closed:
            return {
                "total_pnl": self.total_pnl,
                "win_rate": 0.0,
                "trades": 0
            }

        wins = sum(1 for t in closed if t.pnl > 0)

        self.win_rate = wins / len(closed)

        return {
            "total_pnl": self.total_pnl,
            "win_rate": self.win_rate,
            "trades": len(closed)
        }