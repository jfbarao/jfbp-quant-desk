# 🚧 BUILD MARKER: OP1-0702-A
"""
Decision Packet

A lightweight, source-agnostic handoff contract between JFBP Quant Desk
analysis modules and decision/execution modules.

Producer modules such as Opportunity Center, Options Center, Scanner, or
Research can store one packet in Streamlit session state. Consumer modules
such as Options Decision Center can then load the packet and continue the
workflow without asking the user to re-enter known context.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Any

from options_engine.models.trade_model import TradeModel


@dataclass
class DecisionPacket:
    source: str = ""
    symbol: str = ""
    asset_class: str = "Options"
    mission: str = ""
    recommended_strategy: str = ""
    market_bias: str = ""
    stock_price: float = 0.0
    score: float = 0.0
    institutional_grade: str = ""
    opportunity_grade: str = ""
    confidence: float = 0.0
    next_action: str = ""

    expiration: date | None = None
    strike: float = 0.0
    long_strike: float = 0.0
    premium: float = 0.0
    long_premium: float = 0.0
    contracts: int = 1

    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "DecisionPacket":
        if not isinstance(data, dict):
            return cls()

        # Accept canonical TradeLifecyclePacket dictionaries as input.
        if any(key in data for key in ("identity", "opportunity", "construction", "execution")):
            identity = data.get("identity", {}) if isinstance(data.get("identity"), dict) else {}
            opportunity = data.get("opportunity", {}) if isinstance(data.get("opportunity"), dict) else {}
            construction = data.get("construction", {}) if isinstance(data.get("construction"), dict) else {}
            execution = data.get("execution", {}) if isinstance(data.get("execution"), dict) else {}
            data = {
                **data,
                "source": identity.get("source") or data.get("source") or data.get("metadata", {}).get("last_source", ""),
                "symbol": identity.get("symbol") or data.get("symbol", ""),
                "asset_class": identity.get("asset_class") or data.get("asset_class", "Options"),
                "mission": identity.get("mission") or data.get("mission", ""),
                "recommended_strategy": construction.get("strategy_type") or identity.get("strategy") or data.get("recommended_strategy", ""),
                "market_bias": identity.get("market_bias") or data.get("market_bias", ""),
                "stock_price": identity.get("stock_price") or data.get("stock_price", 0.0),
                "score": construction.get("options_quality") or opportunity.get("institutional_score") or data.get("score", 0.0),
                "institutional_grade": opportunity.get("institutional_grade") or opportunity.get("approval") or data.get("institutional_grade", ""),
                "opportunity_grade": opportunity.get("opportunity_grade") or opportunity.get("approval") or data.get("opportunity_grade", ""),
                "confidence": opportunity.get("confidence") or construction.get("options_quality") or data.get("confidence", 0.0),
                "next_action": opportunity.get("next_action") or data.get("next_action", ""),
                "notes": opportunity.get("notes") or opportunity.get("summary") or data.get("notes", ""),
            }

        allowed = set(cls.__dataclass_fields__.keys())
        clean: dict[str, Any] = {}

        for key, value in data.items():
            if key not in allowed:
                continue

            if key == "expiration" and isinstance(value, str) and value.strip():
                clean[key] = _parse_date(value)
            else:
                clean[key] = value

        return cls(**clean)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if isinstance(self.expiration, date):
            data["expiration"] = self.expiration.isoformat()
        return data

    def has_content(self) -> bool:
        return bool(self.symbol or self.recommended_strategy or self.mission)

    def fingerprint(self) -> str:
        return "|".join(
            [
                self.source,
                self.symbol,
                self.asset_class,
                self.mission,
                self.recommended_strategy,
                str(self.score),
                str(self.confidence),
            ]
        )


def _parse_date(value: str) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    try:
        return date.fromisoformat(text)
    except Exception:
        return None


def get_packet_from_session(session_state: Any) -> DecisionPacket | None:
    """
    Reads the active decision packet from Streamlit session state.

    Supports both the new universal key and the earlier opportunity-specific
    key for backward compatibility.
    """

    raw = session_state.get("trade_lifecycle_packet")
    if not isinstance(raw, dict):
        raw = session_state.get("decision_packet")
    if not isinstance(raw, dict):
        raw = session_state.get("opportunity_packet")

    packet = DecisionPacket.from_dict(raw)
    return packet if packet.has_content() else None


def apply_packet_to_trade(packet: DecisionPacket, trade: TradeModel) -> TradeModel:
    """
    Applies packet context to TradeModel without calculating or validating.
    """

    if packet.symbol:
        trade.symbol = packet.symbol.upper().strip()

    if packet.mission:
        trade.mission = packet.mission
        trade.objective = packet.mission

    if packet.recommended_strategy:
        trade.recommended_strategy = packet.recommended_strategy
        trade.user_selected_strategy = packet.recommended_strategy
        trade.strategy = packet.recommended_strategy

    if packet.market_bias:
        trade.market_bias = packet.market_bias

    if packet.stock_price:
        trade.stock_price = float(packet.stock_price or 0.0)

    if packet.confidence:
        trade.strategy_confidence = float(packet.confidence or 0.0)

    if packet.notes:
        trade.strategy_reason = packet.notes

    if packet.expiration:
        trade.expiration = packet.expiration

    if packet.strike:
        trade.strike = float(packet.strike or 0.0)

    if packet.long_strike:
        trade.long_strike = float(packet.long_strike or 0.0)

    if packet.premium:
        trade.premium = float(packet.premium or 0.0)

    if packet.long_premium:
        trade.long_premium = float(packet.long_premium or 0.0)

    if packet.contracts:
        trade.contracts = max(int(packet.contracts or 1), 1)

    trade.construction_complete = False
    trade.approval_status = "Pending"
    trade.reset_results()
    trade.reset_validation()

    return trade


def clear_packet_from_session(session_state: Any) -> None:
    session_state.pop("decision_packet", None)
    session_state.pop("opportunity_packet", None)
    session_state.pop("options_decision_packet", None)
    session_state.pop("otcc_loaded_packet_fingerprint", None)
