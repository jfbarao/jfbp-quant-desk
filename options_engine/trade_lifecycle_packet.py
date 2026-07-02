"""
Trade Lifecycle Packet v1.1
Mission: TLP-0701-A — Operation ONE PACKET

Canonical trade object for JFBP Quant Desk. This replaces fragmented
DecisionPacket / OpportunityPacket / OptionsPacket handoffs with one staged,
append-only packet that can be enriched from discovery through journal.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict, is_dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from uuid import uuid4
import copy


CANONICAL_SESSION_KEY = "trade_lifecycle_packet"
LEGACY_DECISION_KEY = "decision_packet"
STAGE_MEMORY_KEY = "trade_lifecycle_packet_memory"
PACKET_VERSION = "1.1"


class TradeStage(str, Enum):
    DISCOVERY = "DISCOVERY"
    RESEARCH = "RESEARCH"
    OPPORTUNITY_ANALYSIS = "OPPORTUNITY_ANALYSIS"
    TRADE_CONSTRUCTION = "TRADE_CONSTRUCTION"
    EXECUTION_REVIEW = "EXECUTION_REVIEW"
    ORDER_EXECUTION = "ORDER_EXECUTION"
    POSITION_MANAGEMENT = "POSITION_MANAGEMENT"
    JOURNAL = "JOURNAL"
    COMPLETE = "COMPLETE"


STAGE_ORDER: List[TradeStage] = [
    TradeStage.DISCOVERY,
    TradeStage.RESEARCH,
    TradeStage.OPPORTUNITY_ANALYSIS,
    TradeStage.TRADE_CONSTRUCTION,
    TradeStage.EXECUTION_REVIEW,
    TradeStage.ORDER_EXECUTION,
    TradeStage.POSITION_MANAGEMENT,
    TradeStage.JOURNAL,
    TradeStage.COMPLETE,
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_stage(value: Any) -> TradeStage:
    if isinstance(value, TradeStage):
        return value
    if value is None:
        return TradeStage.DISCOVERY
    try:
        return TradeStage(str(value))
    except Exception:
        value_str = str(value).upper()
        for stage in TradeStage:
            if stage.name == value_str or stage.value == value_str:
                return stage
    return TradeStage.DISCOVERY


def _clean_dict(data: Any) -> Any:
    if isinstance(data, Enum):
        return data.value
    if is_dataclass(data):
        return {k: _clean_dict(v) for k, v in asdict(data).items()}
    if isinstance(data, dict):
        return {k: _clean_dict(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_clean_dict(v) for v in data]
    return data


def _merge_non_null(target: Any, updates: Dict[str, Any], *, overwrite: bool = False) -> None:
    """Merge dict values into a dataclass without replacing existing values unless requested.

    Approval checklist fields must be able to move from
    False -> True and score must be able to move from 0.0 -> calculated value
    without requiring destructive overwrite of the entire packet.
    """
    if not updates:
        return
    for key, value in updates.items():
        if not hasattr(target, key):
            continue
        if value is None:
            continue
        current = getattr(target, key)
        should_update = (
            overwrite
            or current is None
            or current == {}
            or current == []
            or current == ""
            or (isinstance(current, bool) and value is True and current is False)
            or (isinstance(current, (int, float)) and not isinstance(current, bool) and float(current) == 0.0 and _tlp_float(value, 0.0) != 0.0 if "_tlp_float" in globals() else False)
        )
        if should_update:
            setattr(target, key, copy.deepcopy(value))


def _is_contributor_source(source: Any) -> bool:
    text = str(source or "").strip()
    if not text:
        return False
    ignored = {
        "Lifecycle Engine",
        "Shared Lifecycle Engine",
        "legacy_session_import",
        "session_packet_reconcile",
        "symbol_stage_memory_save",
        "symbol_stage_memory_restore",
        "legacy_from_dict",
        "session_legacy",
        "legacy_update",
    }
    return text not in ignored and not text.startswith("legacy_") and not text.startswith("session_")


def _add_unique(items: List[str], value: Any) -> None:
    text = str(value or "").strip()
    if text and text not in items:
        items.append(text)


@dataclass
class TradeIdentity:
    symbol: Optional[str] = None
    asset_class: Optional[str] = None
    strategy: Optional[str] = None
    source: Optional[str] = None
    mission: Optional[str] = None
    market_bias: Optional[str] = None
    stock_price: Optional[float] = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)


@dataclass
class OpportunityAnalysis:
    institutional_score: Optional[float] = None
    approval: Optional[str] = None
    confidence: Optional[float] = None
    summary: Optional[str] = None
    opportunity_grade: Optional[str] = None
    institutional_grade: Optional[str] = None
    next_action: Optional[str] = None
    notes: Optional[str] = None
    completed: bool = False


@dataclass
class TradeConstruction:
    strategy_type: Optional[str] = None
    expiration: Optional[str] = None
    strike: Optional[float] = None
    credit: Optional[float] = None
    debit: Optional[float] = None
    max_profit: Optional[float] = None
    max_loss: Optional[float] = None
    breakeven: Optional[float] = None
    options_quality: Optional[float] = None
    greeks: Dict[str, Any] = field(default_factory=dict)
    completed: bool = False


@dataclass
class ExecutionReview:
    execution_confidence: Optional[float] = None
    position_size: Optional[float] = None
    account: Optional[str] = None
    risk_per_trade: Optional[float] = None
    portfolio_impact: Optional[Any] = None
    approval: Optional[str] = None
    completed: bool = False


@dataclass
class ApprovalReview:
    score: float = 0.0

    trend_confirmed: bool = False
    premium_confirmed: bool = False
    liquidity_confirmed: bool = False
    strike_confirmed: bool = False
    expiration_confirmed: bool = False
    position_size_confirmed: bool = False
    buying_power_confirmed: bool = False
    event_risk_confirmed: bool = False
    risk_reward_confirmed: bool = False

    approved: bool = False
    approved_by: str = ""
    approved_timestamp: str = ""
    notes: str = ""


@dataclass
class OrderLifecycle:
    broker: Optional[str] = None
    order_id: Optional[str] = None
    order_type: Optional[str] = None
    limit_price: Optional[float] = None
    fill_price: Optional[float] = None
    status: Optional[str] = None
    submitted_at: Optional[str] = None
    filled_at: Optional[str] = None
    completed: bool = False


@dataclass
class JournalRecord:
    entry_notes: Optional[str] = None
    exit_notes: Optional[str] = None
    pnl: Optional[float] = None
    rating: Optional[str] = None
    lessons: Optional[str] = None
    closed_at: Optional[str] = None
    completed: bool = False


@dataclass
class PacketMetadata:
    packet_id: str = field(default_factory=lambda: f"tlp_{uuid4().hex[:12]}")
    version: str = PACKET_VERSION
    current_stage: TradeStage = TradeStage.DISCOVERY
    completed_stages: List[str] = field(default_factory=list)
    last_source: Optional[str] = None
    contributors: List[str] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TradeLifecyclePacket:
    identity: TradeIdentity = field(default_factory=TradeIdentity)
    opportunity: OpportunityAnalysis = field(default_factory=OpportunityAnalysis)
    construction: TradeConstruction = field(default_factory=TradeConstruction)
    execution: ExecutionReview = field(default_factory=ExecutionReview)
    approval: ApprovalReview = field(default_factory=ApprovalReview)
    order: OrderLifecycle = field(default_factory=OrderLifecycle)
    journal: JournalRecord = field(default_factory=JournalRecord)
    metadata: PacketMetadata = field(default_factory=PacketMetadata)
    status: str = "DRAFT"

    @classmethod
    def create(
        cls,
        symbol: Optional[str] = None,
        source: Optional[str] = None,
        asset_class: Optional[str] = None,
        strategy: Optional[str] = None,
        **kwargs: Any,
    ) -> "TradeLifecyclePacket":
        packet = cls()
        packet.identity.symbol = symbol
        packet.identity.source = source
        packet.identity.asset_class = asset_class
        packet.identity.strategy = strategy
        packet.metadata.last_source = source
        packet._record("create", source=source, details={"symbol": symbol, "asset_class": asset_class, "strategy": strategy})
        if kwargs:
            packet.merge_update(kwargs, source=source)
        return packet

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "TradeLifecyclePacket":
        if not isinstance(data, dict):
            return cls()

        # Accept already-clean canonical dictionaries.
        packet = cls()
        identity_data = data.get("identity") if isinstance(data.get("identity"), dict) else {}
        opportunity_data = data.get("opportunity") if isinstance(data.get("opportunity"), dict) else {}
        construction_data = data.get("construction") if isinstance(data.get("construction"), dict) else {}
        execution_data = data.get("execution") if isinstance(data.get("execution"), dict) else {}
        approval_data = data.get("approval") if isinstance(data.get("approval"), dict) else {}
        order_data = data.get("order") if isinstance(data.get("order"), dict) else {}
        journal_data = data.get("journal") if isinstance(data.get("journal"), dict) else {}
        metadata_data = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}

        packet.identity = TradeIdentity(**{**asdict(packet.identity), **identity_data})
        packet.opportunity = OpportunityAnalysis(**{**asdict(packet.opportunity), **opportunity_data})
        packet.construction = TradeConstruction(**{**asdict(packet.construction), **construction_data})
        packet.execution = ExecutionReview(**{**asdict(packet.execution), **execution_data})
        packet.approval = ApprovalReview(**{**asdict(packet.approval), **approval_data})
        packet.order = OrderLifecycle(**{**asdict(packet.order), **order_data})
        packet.journal = JournalRecord(**{**asdict(packet.journal), **journal_data})

        md = {**asdict(packet.metadata), **metadata_data}
        md["current_stage"] = _coerce_stage(md.get("current_stage"))
        packet.metadata = PacketMetadata(**md)
        packet.status = str(data.get("status") or packet.status or "DRAFT")
        if packet.approval.approved:
            packet.status = "APPROVED"

        # Accept legacy flat values if present.
        legacy_updates: Dict[str, Any] = {}
        for key in ("symbol", "selected_symbol", "trade_symbol", "option_symbol"):
            if data.get(key) and not packet.identity.symbol:
                legacy_updates.setdefault("identity", {})["symbol"] = data.get(key)
                break
        for key in ("source", "asset_class", "mission", "market_bias", "stock_price"):
            if data.get(key) is not None:
                legacy_updates.setdefault("identity", {})[key] = data.get(key)
        for key in ("recommended_strategy", "strategy", "user_selected_strategy"):
            if data.get(key) and not packet.identity.strategy:
                legacy_updates.setdefault("identity", {})["strategy"] = data.get(key)
                legacy_updates.setdefault("construction", {})["strategy_type"] = data.get(key)
                break
        if data.get("institutional_score") is not None or data.get("opportunity_score") is not None or data.get("score") is not None:
            legacy_updates.setdefault("opportunity", {})["institutional_score"] = data.get("institutional_score") or data.get("opportunity_score") or data.get("score")
        if data.get("confidence") is not None:
            legacy_updates.setdefault("opportunity", {})["confidence"] = data.get("confidence")
        if data.get("approval") is not None and not isinstance(data.get("approval"), dict):
            legacy_updates.setdefault("opportunity", {})["approval"] = data.get("approval")
        if data.get("opportunity_grade") is not None:
            legacy_updates.setdefault("opportunity", {})["opportunity_grade"] = data.get("opportunity_grade")
        if data.get("institutional_grade") is not None:
            legacy_updates.setdefault("opportunity", {})["institutional_grade"] = data.get("institutional_grade")
        if data.get("next_action") is not None:
            legacy_updates.setdefault("opportunity", {})["next_action"] = data.get("next_action")
        if data.get("notes") is not None or data.get("reason") is not None:
            legacy_updates.setdefault("opportunity", {})["notes"] = data.get("notes") or data.get("reason")
        if data.get("options_quality") is not None:
            legacy_updates.setdefault("construction", {})["options_quality"] = data.get("options_quality")
        if data.get("execution_confidence") is not None:
            legacy_updates.setdefault("execution", {})["execution_confidence"] = data.get("execution_confidence")
        if data.get("approval_score") is not None:
            legacy_updates.setdefault("approval", {})["score"] = data.get("approval_score")
        if data.get("approved") is not None:
            legacy_updates.setdefault("approval", {})["approved"] = bool(data.get("approved"))
        if legacy_updates:
            packet.merge_update(legacy_updates, source="legacy_from_dict")
        return packet

    def to_dict(self) -> Dict[str, Any]:
        return _clean_dict(self)

    @classmethod
    def from_session(cls, session_state: Optional[Dict[str, Any]] = None) -> "TradeLifecyclePacket":
        """Load the one canonical lifecycle packet and reconcile legacy mirrors.

        OP1-0701-H rule: pages may still write legacy keys during migration,
        but loading a packet must never ignore compatible legacy data. This
        prevents the last page opened from becoming an isolated island.
        """
        ss = session_state if session_state is not None else _streamlit_session_state()

        candidates: List[TradeLifecyclePacket] = []

        def _append_raw(raw: Any) -> None:
            if isinstance(raw, cls):
                candidates.append(raw)
            elif isinstance(raw, dict):
                candidates.append(cls.from_dict(raw))
                embedded = raw.get(CANONICAL_SESSION_KEY) or raw.get("trade_lifecycle_packet")
                if isinstance(embedded, dict):
                    candidates.append(cls.from_dict(embedded))

        # 1) Active packet + legacy mirrors.
        for key in (CANONICAL_SESSION_KEY, LEGACY_DECISION_KEY, "opportunity_packet", "options_decision_packet"):
            _append_raw(ss.get(key))

        # 2) Symbol-indexed stage memory. This is the OP1-0701-H fix: even if
        # a page overwrites the active packet, previously completed stages for
        # the same symbol are kept here and merged back on load.
        requested_symbol = str(
            ss.get("selected_symbol")
            or ss.get("trade_symbol")
            or ss.get("option_symbol")
            or ss.get("options_manual_symbol")
            or ss.get("symbol")
            or ""
        ).upper().strip()
        memory = ss.get(STAGE_MEMORY_KEY, {})
        if isinstance(memory, dict):
            if requested_symbol and isinstance(memory.get(requested_symbol), dict):
                _append_raw(memory.get(requested_symbol))
            # Also include all memory candidates; merge_from_packet protects
            # against symbol mismatch.
            for remembered in memory.values():
                _append_raw(remembered)

        packet = next((item for item in candidates if item.has_content()), None)
        if packet is None:
            packet = cls.create(symbol=requested_symbol or None, source="session_legacy")

        for candidate in candidates:
            if candidate is packet or not candidate.has_content():
                continue
            packet.merge_from_packet(candidate, source="session_packet_reconcile", overwrite=False)

        # Pull non-destructive scalar session values into canonical packet.
        packet.merge_update(
            {
                "identity": {
                    "symbol": ss.get("selected_symbol") or ss.get("trade_symbol") or ss.get("option_symbol") or ss.get("symbol"),
                },
                "opportunity": {
                    "institutional_score": ss.get("institutional_score"),
                    "confidence": ss.get("confidence"),
                    "approval": ss.get("approval"),
                },
                "construction": {"options_quality": ss.get("options_quality")},
                "execution": {"execution_confidence": ss.get("execution_confidence")},
            },
            source="legacy_session_import",
        )
        return packet

    def save_to_session(self, session_state: Optional[Dict[str, Any]] = None, *, mirror_legacy: bool = True) -> "TradeLifecyclePacket":
        ss = session_state if session_state is not None else _streamlit_session_state()
        self.touch()

        # OP1-0701-H: preserve a per-symbol merged lifecycle copy before
        # writing the active packet. This prevents Opportunity Center, Options
        # Center, and Trade Command from acting like separate islands when one
        # page still writes a legacy mirror.
        symbol_key = str(self.identity.symbol or "").upper().strip()
        if symbol_key:
            memory = ss.get(STAGE_MEMORY_KEY)
            if not isinstance(memory, dict):
                memory = {}
            remembered_raw = memory.get(symbol_key)
            remembered = TradeLifecyclePacket.from_dict(remembered_raw) if isinstance(remembered_raw, dict) else None
            if remembered is not None and remembered.has_content():
                remembered.merge_from_packet(self, source="symbol_stage_memory_save", overwrite=False)
                self.merge_from_packet(remembered, source="symbol_stage_memory_restore", overwrite=False)
            memory[symbol_key] = self.to_dict()
            ss[STAGE_MEMORY_KEY] = memory

        ss[CANONICAL_SESSION_KEY] = self.to_dict()
        if mirror_legacy:
            ss[LEGACY_DECISION_KEY] = self.to_dict()
            if self.identity.symbol:
                ss["selected_symbol"] = self.identity.symbol
                ss["trade_symbol"] = self.identity.symbol
                ss["option_symbol"] = self.identity.symbol
            if self.opportunity.institutional_score is not None:
                ss["institutional_score"] = self.opportunity.institutional_score
            if self.construction.options_quality is not None:
                ss["options_quality"] = self.construction.options_quality
            if self.execution.execution_confidence is not None:
                ss["execution_confidence"] = self.execution.execution_confidence
        return self

    def merge_from_packet(self, other: "TradeLifecyclePacket", *, source: Optional[str] = None, overwrite: bool = False) -> "TradeLifecyclePacket":
        """Merge another packet into this one without wiping completed stages.

        Sections are only merged when the symbols are compatible. This is the
        OP1-0701-H guardrail that allows Opportunity Center, Options Center,
        and Trade Command to enrich one trade without replacing one another.
        """
        if other is None or not isinstance(other, TradeLifecyclePacket):
            return self
        my_symbol = str(self.identity.symbol or "").upper().strip()
        other_symbol = str(other.identity.symbol or "").upper().strip()
        if my_symbol and other_symbol and my_symbol != other_symbol:
            self._record("merge_from_packet_skipped_symbol_mismatch", source=source, details={"existing": my_symbol, "incoming": other_symbol})
            return self

        self.merge_update(other.to_dict(), source=source or other.metadata.last_source or other.identity.source, overwrite=overwrite)
        for stage in other.metadata.completed_stages or []:
            if stage not in self.metadata.completed_stages:
                self.metadata.completed_stages.append(stage)
        self.metadata.history.extend(copy.deepcopy(other.metadata.history or [])[-10:])
        self.metadata.history = self.metadata.history[-50:]
        return self

    @staticmethod
    def _symbol_changed(packet: "TradeLifecyclePacket", incoming_symbol: Any) -> bool:
        existing = str(packet.identity.symbol or "").upper().strip()
        incoming = str(incoming_symbol or "").upper().strip()
        return bool(existing and incoming and existing != incoming)

    @classmethod
    def update_opportunity_in_session(cls, session_state: Optional[Dict[str, Any]] = None, *, source: str = "Opportunity Center", overwrite: bool = False, **fields: Any) -> "TradeLifecyclePacket":
        ss = session_state if session_state is not None else _streamlit_session_state()
        packet = cls.from_session(ss)
        symbol = fields.pop("symbol", None)
        if cls._symbol_changed(packet, symbol):
            symbol_key = str(symbol or "").upper().strip()
            memory = ss.get(STAGE_MEMORY_KEY, {})
            remembered = cls.from_dict(memory.get(symbol_key)) if isinstance(memory, dict) and isinstance(memory.get(symbol_key), dict) else None
            if remembered is not None and remembered.has_content():
                packet = remembered
            else:
                packet = cls.create(symbol=symbol_key, source=source, asset_class=fields.get("asset_class") or "Options", strategy=fields.get("strategy"))
        packet.merge_update({"identity": {"symbol": symbol, "asset_class": fields.pop("asset_class", None), "strategy": fields.pop("strategy", None), "mission": fields.pop("mission", None)}, "opportunity": fields}, source=source, overwrite=overwrite)
        packet.mark_stage_complete(TradeStage.OPPORTUNITY_ANALYSIS, source=source)
        return packet.save_to_session(session_state)

    @classmethod
    def update_construction_in_session(cls, session_state: Optional[Dict[str, Any]] = None, *, source: str = "Options Center", overwrite: bool = False, **fields: Any) -> "TradeLifecyclePacket":
        ss = session_state if session_state is not None else _streamlit_session_state()
        packet = cls.from_session(ss)
        symbol = fields.pop("symbol", None)
        if cls._symbol_changed(packet, symbol):
            # Try the symbol memory before creating a blank packet.
            symbol_key = str(symbol or "").upper().strip()
            memory = ss.get(STAGE_MEMORY_KEY, {})
            remembered = cls.from_dict(memory.get(symbol_key)) if isinstance(memory, dict) and isinstance(memory.get(symbol_key), dict) else None
            if remembered is not None and remembered.has_content():
                packet = remembered
            else:
                packet = cls.create(symbol=symbol_key, source=source, asset_class=fields.get("asset_class") or "Options", strategy=fields.get("strategy"))
        identity_updates = {
            "symbol": symbol,
            "asset_class": fields.pop("asset_class", None),
            "strategy": fields.pop("strategy", None),
            "mission": fields.pop("mission", None),
            "market_bias": fields.pop("market_bias", None),
            "stock_price": fields.pop("stock_price", None),
        }
        packet.merge_update({"identity": identity_updates, "construction": fields}, source=source, overwrite=overwrite)
        packet.mark_stage_complete(TradeStage.TRADE_CONSTRUCTION, source=source)
        return packet.save_to_session(session_state)

    @classmethod
    def update_execution_in_session(cls, session_state: Optional[Dict[str, Any]] = None, *, source: str = "Trade Command Center", overwrite: bool = False, **fields: Any) -> "TradeLifecyclePacket":
        ss = session_state if session_state is not None else _streamlit_session_state()
        packet = cls.from_session(ss)
        symbol = fields.pop("symbol", None)
        if cls._symbol_changed(packet, symbol):
            symbol_key = str(symbol or "").upper().strip()
            memory = ss.get(STAGE_MEMORY_KEY, {})
            remembered = cls.from_dict(memory.get(symbol_key)) if isinstance(memory, dict) and isinstance(memory.get(symbol_key), dict) else None
            if remembered is not None and remembered.has_content():
                packet = remembered
            else:
                packet = cls.create(symbol=symbol_key, source=source, asset_class=fields.get("asset_class") or "Options", strategy=fields.get("strategy"))
        identity_updates = {"symbol": symbol, "strategy": fields.pop("strategy", None)}
        packet.merge_update({"identity": identity_updates, "execution": fields}, source=source, overwrite=overwrite)
        packet.mark_stage_complete(TradeStage.EXECUTION_REVIEW, source=source)
        return packet.save_to_session(session_state)

    def merge_update(self, updates: Dict[str, Any], *, source: Optional[str] = None, overwrite: bool = False) -> "TradeLifecyclePacket":
        if not updates:
            return self

        # Accept flat legacy updates.
        if any(k in updates for k in ("symbol", "selected_symbol", "trade_symbol", "option_symbol")):
            symbol = updates.get("symbol") or updates.get("selected_symbol") or updates.get("trade_symbol") or updates.get("option_symbol")
            updates.setdefault("identity", {})["symbol"] = symbol
        flat_map = {
            "source": ("identity", "source"),
            "asset_class": ("identity", "asset_class"),
            "mission": ("identity", "mission"),
            "market_bias": ("identity", "market_bias"),
            "stock_price": ("identity", "stock_price"),
            "recommended_strategy": ("construction", "strategy_type"),
            "strategy": ("construction", "strategy_type"),
            "institutional_score": ("opportunity", "institutional_score"),
            "opportunity_score": ("opportunity", "institutional_score"),
            "score": ("opportunity", "institutional_score"),
            "confidence": ("opportunity", "confidence"),
            "approval": ("opportunity", "approval"),
            "summary": ("opportunity", "summary"),
            "opportunity_grade": ("opportunity", "opportunity_grade"),
            "institutional_grade": ("opportunity", "institutional_grade"),
            "next_action": ("opportunity", "next_action"),
            "notes": ("opportunity", "notes"),
            "reason": ("opportunity", "notes"),
            "options_quality": ("construction", "options_quality"),
            "strategy_type": ("construction", "strategy_type"),
            "expiration": ("construction", "expiration"),
            "strike": ("construction", "strike"),
            "credit": ("construction", "credit"),
            "debit": ("construction", "debit"),
            "max_profit": ("construction", "max_profit"),
            "max_loss": ("construction", "max_loss"),
            "breakeven": ("construction", "breakeven"),
            "greeks": ("construction", "greeks"),
            "execution_confidence": ("execution", "execution_confidence"),
            "position_size": ("execution", "position_size"),
            "account": ("execution", "account"),
            "risk_per_trade": ("execution", "risk_per_trade"),
            "portfolio_impact": ("execution", "portfolio_impact"),
            "approval_score": ("approval", "score"),
            "approved": ("approval", "approved"),
            "approved_by": ("approval", "approved_by"),
            "approved_timestamp": ("approval", "approved_timestamp"),
            "approval_notes": ("approval", "notes"),
        }
        for flat_key, (section, field_name) in flat_map.items():
            if flat_key in updates:
                # Canonical approval is a dict section. A flat
                # legacy approval string still maps to opportunity.approval,
                # but an approval dict must remain packet.approval.
                if flat_key == "approval" and isinstance(updates.get("approval"), dict):
                    continue
                updates.setdefault(section, {})[field_name] = updates.get(flat_key)

        if "status" in updates and updates.get("status"):
            self.status = str(updates.get("status") or self.status or "DRAFT")

        for section_name in ("identity", "opportunity", "construction", "execution", "approval", "order", "journal"):
            section_updates = updates.get(section_name)
            if isinstance(section_updates, dict):
                _merge_non_null(getattr(self, section_name), section_updates, overwrite=overwrite)

        if self.approval.approved:
            self.status = "APPROVED"
        elif not self.status:
            self.status = "DRAFT"

        if source:
            self.metadata.last_source = source
        self.touch()
        self._record("merge_update", source=source, details={"sections": list(updates.keys()), "overwrite": overwrite})
        return self

    def advance_stage(self, stage: Optional[Any] = None, *, source: Optional[str] = None) -> "TradeLifecyclePacket":
        if stage is not None:
            next_stage = _coerce_stage(stage)
        else:
            current = _coerce_stage(self.metadata.current_stage)
            try:
                idx = STAGE_ORDER.index(current)
                next_stage = STAGE_ORDER[min(idx + 1, len(STAGE_ORDER) - 1)]
            except ValueError:
                next_stage = TradeStage.DISCOVERY
        self.metadata.current_stage = next_stage
        if source:
            self.metadata.last_source = source
        self.touch()
        self._record("advance_stage", source=source, details={"stage": next_stage.value})
        return self

    def mark_stage_complete(self, stage: Any, *, source: Optional[str] = None) -> "TradeLifecyclePacket":
        stage_obj = _coerce_stage(stage)
        if stage_obj.value not in self.metadata.completed_stages:
            self.metadata.completed_stages.append(stage_obj.value)
        if stage_obj == TradeStage.OPPORTUNITY_ANALYSIS:
            self.opportunity.completed = True
        elif stage_obj == TradeStage.TRADE_CONSTRUCTION:
            self.construction.completed = True
        elif stage_obj == TradeStage.EXECUTION_REVIEW:
            self.execution.completed = True
        elif stage_obj == TradeStage.ORDER_EXECUTION:
            self.order.completed = True
        elif stage_obj in (TradeStage.JOURNAL, TradeStage.COMPLETE):
            self.journal.completed = True
        if source:
            self.metadata.last_source = source
        self.touch()
        self._record("mark_stage_complete", source=source, details={"stage": stage_obj.value})
        return self

    def touch(self) -> None:
        self.identity.updated_at = _now_iso()

    def _record(self, event: str, *, source: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
        if _is_contributor_source(source):
            _add_unique(self.metadata.contributors, source)
        self.metadata.history.append(
            {
                "timestamp": _now_iso(),
                "event": event,
                "source": source,
                "details": details or {},
            }
        )
        # Prevent session bloat.
        self.metadata.history = self.metadata.history[-50:]


    # ------------------------------------------------------------------
    # Legacy DecisionPacket compatibility surface
    # ------------------------------------------------------------------
    def has_content(self) -> bool:
        return bool(
            self.identity.symbol
            or self.identity.strategy
            or self.construction.strategy_type
            or self.identity.mission
            or self.opportunity.institutional_score is not None
            or self.construction.options_quality is not None
            or float(self.approval.score or 0.0) > 0.0
            or bool(self.approval.approved)
        )

    def fingerprint(self) -> str:
        parts = [
            self.metadata.packet_id,
            self.metadata.version,
            str(_coerce_stage(self.metadata.current_stage).value),
            str(self.identity.source or ""),
            str(self.identity.symbol or ""),
            str(self.identity.asset_class or ""),
            str(self.identity.mission or ""),
            str(self.construction.strategy_type or self.identity.strategy or ""),
            str(self.opportunity.institutional_score or ""),
            str(self.construction.options_quality or ""),
            str(self.execution.execution_confidence or ""),
            str(self.approval.score or ""),
            str(self.approval.approved),
            str(self.status or ""),
            str(self.identity.updated_at or ""),
        ]
        return "|".join(parts)

    @property
    def source(self) -> str:
        # OP1-0701-H: source is the lifecycle owner, not the page that
        # contributed the last score. Page/module names live in contributors.
        return "Lifecycle Engine" if self.has_content() else str(self.metadata.last_source or self.identity.source or "")

    @property
    def contributors(self) -> List[str]:
        contributors: List[str] = []
        for item in getattr(self.metadata, "contributors", []) or []:
            if _is_contributor_source(item):
                _add_unique(contributors, item)
        for item in self.metadata.history or []:
            if isinstance(item, dict) and _is_contributor_source(item.get("source")):
                _add_unique(contributors, item.get("source"))
        if _is_contributor_source(self.identity.source):
            _add_unique(contributors, self.identity.source)
        if _is_contributor_source(self.metadata.last_source):
            _add_unique(contributors, self.metadata.last_source)
        return contributors

    def contributors_label(self) -> str:
        return " / ".join(self.contributors) if self.contributors else "Pending"

    @source.setter
    def source(self, value: Any) -> None:
        self.identity.source = str(value or "") or None
        self.metadata.last_source = self.identity.source
        if _is_contributor_source(self.identity.source):
            _add_unique(self.metadata.contributors, self.identity.source)

    @property
    def symbol(self) -> str:
        return str(self.identity.symbol or "")

    @symbol.setter
    def symbol(self, value: Any) -> None:
        self.identity.symbol = str(value or "").upper().strip() or None

    @property
    def asset_class(self) -> str:
        return str(self.identity.asset_class or "Options")

    @asset_class.setter
    def asset_class(self, value: Any) -> None:
        self.identity.asset_class = str(value or "") or None

    @property
    def mission(self) -> str:
        return str(self.identity.mission or "")

    @mission.setter
    def mission(self, value: Any) -> None:
        self.identity.mission = str(value or "") or None

    @property
    def recommended_strategy(self) -> str:
        return str(self.construction.strategy_type or self.identity.strategy or "")

    @recommended_strategy.setter
    def recommended_strategy(self, value: Any) -> None:
        text = str(value or "").strip()
        self.identity.strategy = text or None
        self.construction.strategy_type = text or None

    @property
    def strategy(self) -> str:
        return self.recommended_strategy

    @strategy.setter
    def strategy(self, value: Any) -> None:
        self.recommended_strategy = value

    @property
    def market_bias(self) -> str:
        return str(self.identity.market_bias or "")

    @market_bias.setter
    def market_bias(self, value: Any) -> None:
        self.identity.market_bias = str(value or "") or None

    @property
    def stock_price(self) -> float:
        try:
            return float(self.identity.stock_price or 0.0)
        except Exception:
            return 0.0

    @stock_price.setter
    def stock_price(self, value: Any) -> None:
        try:
            self.identity.stock_price = float(value or 0.0)
        except Exception:
            self.identity.stock_price = None

    @property
    def score(self) -> float:
        return float(self.construction.options_quality or self.opportunity.institutional_score or 0.0)

    @score.setter
    def score(self, value: Any) -> None:
        try:
            self.opportunity.institutional_score = float(value or 0.0)
        except Exception:
            pass

    @property
    def confidence(self) -> float:
        return float(self.opportunity.confidence or self.construction.options_quality or self.opportunity.institutional_score or 0.0)

    @confidence.setter
    def confidence(self, value: Any) -> None:
        try:
            self.opportunity.confidence = float(value or 0.0)
        except Exception:
            pass

    @property
    def opportunity_grade(self) -> str:
        return str(self.opportunity.opportunity_grade or self.opportunity.approval or "")

    @opportunity_grade.setter
    def opportunity_grade(self, value: Any) -> None:
        self.opportunity.opportunity_grade = str(value or "") or None

    @property
    def institutional_grade(self) -> str:
        return str(self.opportunity.institutional_grade or self.opportunity.approval or "")

    @institutional_grade.setter
    def institutional_grade(self, value: Any) -> None:
        self.opportunity.institutional_grade = str(value or "") or None

    @property
    def next_action(self) -> str:
        return str(self.opportunity.next_action or "")

    @next_action.setter
    def next_action(self, value: Any) -> None:
        self.opportunity.next_action = str(value or "") or None

    @property
    def notes(self) -> str:
        return str(self.opportunity.notes or self.opportunity.summary or "")

    @notes.setter
    def notes(self, value: Any) -> None:
        self.opportunity.notes = str(value or "") or None

    def to_legacy_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "contributors": self.contributors,
            "contributors_label": self.contributors_label(),
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "mission": self.mission,
            "recommended_strategy": self.recommended_strategy,
            "strategy": self.strategy,
            "market_bias": self.market_bias,
            "stock_price": self.stock_price,
            "score": self.score,
            "institutional_score": self.opportunity.institutional_score,
            "opportunity_score": self.opportunity.institutional_score,
            "options_quality": self.construction.options_quality,
            "options_quality_score": self.construction.options_quality,
            "execution_confidence": self.execution.execution_confidence,
            "approval_score": self.approval.score,
            "approved": self.approval.approved,
            "packet_status": self.status,
            "institutional_grade": self.institutional_grade,
            "opportunity_grade": self.opportunity_grade,
            "confidence": self.confidence,
            "next_action": self.next_action,
            "notes": self.notes,
            "trade_lifecycle_packet": self.to_dict(),
        }

    def stage_value(self, stage: TradeStage) -> Optional[Any]:
        if stage == TradeStage.OPPORTUNITY_ANALYSIS:
            return self.opportunity.institutional_score
        if stage == TradeStage.TRADE_CONSTRUCTION:
            return self.construction.options_quality
        if stage == TradeStage.EXECUTION_REVIEW:
            return self.execution.execution_confidence
        return None

    def stage_label(self, stage: TradeStage) -> str:
        labels = {
            TradeStage.OPPORTUNITY_ANALYSIS: "Opportunity Analysis",
            TradeStage.TRADE_CONSTRUCTION: "Trade Construction",
            TradeStage.EXECUTION_REVIEW: "Execution Review",
        }
        return labels.get(stage, stage.value.replace("_", " ").title())

    def stage_display(self, stage: TradeStage) -> str:
        value = self.stage_value(stage)
        if value is not None:
            return f"{value:g}" if isinstance(value, (int, float)) else str(value)
        waiting = {
            TradeStage.OPPORTUNITY_ANALYSIS: "Waiting for Opportunity Center...",
            TradeStage.TRADE_CONSTRUCTION: "Waiting for Options Trade Construction Center...",
            TradeStage.EXECUTION_REVIEW: "Waiting for Trade Command Center...",
        }
        return waiting.get(stage, "Waiting for previous stage...")



# ============================================================
# Shared Lifecycle Scoring Engine — OP1-0701-H
# ============================================================

def _tlp_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.replace("%", "").replace("$", "").replace(",", "").strip()
            if not value:
                return default
        return float(value)
    except Exception:
        return default


def _tlp_score(value: Any) -> Optional[float]:
    number = _tlp_float(value, 0.0)
    if number <= 0:
        return None
    return max(0.0, min(100.0, number))


def _tlp_first_score(*values: Any) -> Optional[float]:
    for value in values:
        score = _tlp_score(value)
        if score is not None:
            return score
    return None


def _tlp_get(session_state: Optional[Dict[str, Any]], key: str, default: Any = None) -> Any:
    try:
        return session_state.get(key, default) if session_state is not None else default
    except Exception:
        return default


def _tlp_rows(session_state: Optional[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    rows = _tlp_get(session_state, key, [])
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _tlp_symbol_from_any(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("symbol", "display_symbol", "selected_symbol", "trade_symbol", "underlying", "ticker"):
            text = _tlp_symbol_from_any(value.get(key))
            if text:
                return text
        return ""
    return str(value or "").upper().strip().split(" ")[0]


def _tlp_find_symbol_row(session_state: Optional[Dict[str, Any]], symbol: str) -> Dict[str, Any]:
    target = _tlp_symbol_from_any(symbol)
    if not target:
        return {}
    for list_key in (
        "opportunity_center_rows",
        "opportunity_rows",
        "scanner_last_raw_signals",
        "scanner_last_results",
        "scanner_results",
        "scanner_last_risk_plan",
    ):
        for row in _tlp_rows(session_state, list_key):
            row_symbol = _tlp_symbol_from_any(row)
            if row_symbol == target:
                return row
    return {}


def _tlp_infer_symbol(packet: TradeLifecyclePacket, session_state: Optional[Dict[str, Any]], trade: Any = None) -> str:
    for value in (
        packet.identity.symbol,
        getattr(trade, "symbol", None),
        _tlp_get(session_state, "selected_symbol"),
        _tlp_get(session_state, "trade_symbol"),
        _tlp_get(session_state, "option_symbol"),
        _tlp_get(session_state, "options_symbol"),
        _tlp_get(session_state, "trade_command_symbol"),
        _tlp_get(session_state, "research_ticker"),
    ):
        text = _tlp_symbol_from_any(value)
        if text:
            return text
    return ""


def _tlp_infer_strategy(packet: TradeLifecyclePacket, session_state: Optional[Dict[str, Any]], trade: Any = None) -> str:
    for value in (
        packet.construction.strategy_type,
        packet.identity.strategy,
        getattr(trade, "strategy", None),
        getattr(trade, "recommended_strategy", None),
        getattr(trade, "user_selected_strategy", None),
        _tlp_get(session_state, "recommended_strategy"),
        _tlp_get(session_state, "options_strategy"),
    ):
        text = str(value or "").strip()
        if text:
            return text
    best = _tlp_get(session_state, "options_best_opportunity", {})
    if isinstance(best, dict):
        return str(best.get("strategy") or "").strip()
    return ""


def _tlp_infer_opportunity_score(packet: TradeLifecyclePacket, session_state: Optional[Dict[str, Any]], symbol: str) -> Optional[float]:
    if packet.opportunity.institutional_score is not None:
        return _tlp_score(packet.opportunity.institutional_score)

    score = _tlp_first_score(
        _tlp_get(session_state, "opportunity_score"),
        _tlp_get(session_state, "institutional_score"),
        _tlp_get(session_state, "scanner_opportunity_score"),
        _tlp_get(session_state, "opportunity_score_pct"),
    )
    if score is not None:
        return score

    ticket = _tlp_get(session_state, "opportunity_center_handoff_ticket", {})
    if isinstance(ticket, dict) and (not symbol or _tlp_symbol_from_any(ticket) == symbol):
        score = _tlp_first_score(
            ticket.get("institutional_score"),
            ticket.get("opportunity_score"),
            ticket.get("opportunity_score_pct"),
            ticket.get("score"),
            ticket.get("confidence"),
            ticket.get("model_score"),
        )
        if score is not None:
            return score

    row = _tlp_find_symbol_row(session_state, symbol)
    score = _tlp_first_score(
        row.get("institutional_score"),
        row.get("opportunity_score"),
        row.get("opportunity_score_pct"),
        row.get("model_score"),
        row.get("rs_score"),
        row.get("score"),
    )
    if score is not None:
        return score

    # OP1-0701-H: Decision Center can now backfill Opportunity Analysis
    # from the shared Options Center engine when Opportunity Center has not
    # been opened first. This keeps the three-stage briefing populated from
    # one symbol workflow instead of leaving Opportunity Analysis blank.
    scorecard = _tlp_get(session_state, "options_current_scorecard", {})
    if isinstance(scorecard, dict):
        score = _tlp_first_score(scorecard.get("total"), scorecard.get("score"), scorecard.get("options_quality"))
        if score is not None:
            return score

    best = _tlp_get(session_state, "options_best_opportunity", {})
    if isinstance(best, dict) and (not symbol or _tlp_symbol_from_any(best) == symbol):
        score = _tlp_first_score(best.get("opportunity_score"), best.get("institutional_score"), best.get("score"), best.get("options_quality"))
        if score is not None:
            return score

    # Final fair fallback: when construction quality exists but no dedicated
    # Opportunity score exists, use it as a provisional Opportunity Analysis
    # score instead of showing a false waiting state.
    return _tlp_first_score(packet.construction.options_quality)


def _tlp_infer_construction_score(
    packet: TradeLifecyclePacket,
    session_state: Optional[Dict[str, Any]],
    trade: Any,
    opportunity_score: Optional[float],
    strategy: str,
) -> Optional[float]:
    if packet.construction.options_quality is not None:
        return _tlp_score(packet.construction.options_quality)

    scorecard = _tlp_get(session_state, "options_current_scorecard", {})
    if isinstance(scorecard, dict):
        score = _tlp_first_score(scorecard.get("total"), scorecard.get("score"), scorecard.get("options_quality"))
        if score is not None:
            return score

    best = _tlp_get(session_state, "options_best_opportunity", {})
    if isinstance(best, dict):
        score = _tlp_first_score(best.get("score"), best.get("options_quality"), best.get("options_quality_score"))
        if score is not None:
            return score

    score = _tlp_first_score(
        _tlp_get(session_state, "options_quality"),
        _tlp_get(session_state, "options_quality_score"),
        getattr(trade, "strategy_confidence", None),
    )
    if score is not None:
        return score

    # Backend fallback: if a symbol and strategy exist, construct a provisional
    # options-quality score from the upstream opportunity score. This is used
    # only when Options Center has not been opened yet.
    if opportunity_score is not None and strategy:
        blocked = {"No options structure", "No Options Trade", "No New Long Premium", "Pending", ""}
        if strategy in blocked:
            return max(0.0, min(100.0, opportunity_score - 25.0))
        bonus = 4.0 if any(word in strategy for word in ("Spread", "Secured", "Covered")) else 0.0
        return max(0.0, min(100.0, opportunity_score - 6.0 + bonus))
    return None


def _tlp_is_placeholder_execution_score(value: Any) -> bool:
    """Detect old placeholder Decision Review values from OP1 migration builds."""
    try:
        number = float(value)
    except Exception:
        return False
    return abs(number - 35.0) < 0.0001


def _tlp_decision_readiness_score(
    packet: TradeLifecyclePacket,
    session_state: Optional[Dict[str, Any]],
    trade: Any,
    construction_score: Optional[float],
) -> Optional[float]:
    """Compute a real Options Decision readiness score from available evidence.

    This replaces the old hard-coded/migrated 35 placeholder. The score is a
    checklist-weighted readiness measure, not another opportunity score.
    """
    if packet is None and trade is None:
        return None

    symbol = str(getattr(packet.identity, "symbol", "") or getattr(trade, "symbol", "") or "").strip() if packet else str(getattr(trade, "symbol", "") or "").strip()
    strategy = str(
        getattr(packet.construction, "strategy_type", "")
        or getattr(packet.identity, "strategy", "")
        or getattr(trade, "strategy", "")
        or getattr(trade, "recommended_strategy", "")
        or ""
    ).strip() if packet else str(getattr(trade, "strategy", "") or getattr(trade, "recommended_strategy", "") or "").strip()

    opportunity_score = _tlp_score(getattr(packet.opportunity, "institutional_score", None)) if packet else None
    construction = construction_score or (_tlp_score(getattr(packet.construction, "options_quality", None)) if packet else None)

    score = 0.0
    max_score = 0.0

    def add(weight: float, passed: bool) -> None:
        nonlocal score, max_score
        max_score += float(weight)
        if passed:
            score += float(weight)

    add(8, bool(symbol))
    add(10, bool(strategy) and strategy not in {"Pending", "No Options Trade", "No options structure", "No New Long Premium"})
    add(12, opportunity_score is not None and opportunity_score >= 60)
    add(18, construction is not None and construction >= 60)

    if trade is not None:
        construction_complete = bool(getattr(trade, "construction_complete", False))
        approval = str(getattr(trade, "approval_status", "") or "").upper().strip()
        validation = str(getattr(trade, "validation_status", "") or "").upper().strip()
        premium = _tlp_float(getattr(trade, "premium", 0.0), 0.0)
        contracts = _tlp_float(getattr(trade, "contracts", 0.0), 0.0)
        buying_power_required = _tlp_float(getattr(trade, "buying_power_required", 0.0), 0.0)
        buying_power = _tlp_float(getattr(trade, "buying_power", 0.0), 0.0)
        max_risk_allowed = _tlp_float(getattr(trade, "max_risk_allowed", 0.0), 0.0)
        max_loss = _tlp_float(getattr(trade, "max_loss", 0.0), 0.0)
        breakeven = _tlp_float(getattr(trade, "breakeven", 0.0), 0.0)
        stock_price = _tlp_float(getattr(trade, "stock_price", 0.0), 0.0) or _tlp_float(getattr(packet.identity, "stock_price", 0.0), 0.0) if packet else _tlp_float(getattr(trade, "stock_price", 0.0), 0.0)

        add(8, premium > 0)
        add(8, contracts >= 1)
        add(10, buying_power <= 0 or buying_power_required <= 0 or buying_power_required <= buying_power)
        add(10, max_risk_allowed <= 0 or max_loss <= 0 or max_loss <= max_risk_allowed)
        add(8, breakeven <= 0 or stock_price <= 0 or breakeven <= stock_price or "CALL" in strategy.upper())
        add(8, validation in {"PASS", "APPROVED", "OK"} or "PASS" in validation or "APPROVED" in approval)
        add(10, construction_complete or "APPROVED" in approval)
        add(8, "REJECT" not in approval and "FAIL" not in validation)
    else:
        # Without local trade form data, this is only a pre-decision packet.
        add(30, False)

    if max_score <= 0:
        return None
    readiness = max(0.0, min(100.0, round((score / max_score) * 100.0, 1)))
    return readiness if readiness > 0 else None


def _tlp_approval_checklist_score(packet: TradeLifecyclePacket) -> float:
    """Calculate Commander Jimmy approval readiness from the canonical checklist."""
    checks = [
        bool(packet.approval.trend_confirmed),
        bool(packet.approval.premium_confirmed),
        bool(packet.approval.liquidity_confirmed),
        bool(packet.approval.strike_confirmed),
        bool(packet.approval.expiration_confirmed),
        bool(packet.approval.position_size_confirmed),
        bool(packet.approval.buying_power_confirmed),
        bool(packet.approval.event_risk_confirmed),
        bool(packet.approval.risk_reward_confirmed),
    ]
    return round((sum(checks) / len(checks)) * 100.0, 1) if checks else 0.0


def _tlp_infer_execution_score(
    packet: TradeLifecyclePacket,
    session_state: Optional[Dict[str, Any]],
    trade: Any,
    construction_score: Optional[float],
) -> Optional[float]:
    existing = packet.execution.execution_confidence
    computed = _tlp_decision_readiness_score(packet, session_state, trade, construction_score)

    # OP1-0702-A: retire the old migration placeholder 35.0 when a real
    # readiness score can be computed from the current packet/trade.
    if existing is not None and not _tlp_is_placeholder_execution_score(existing):
        return _tlp_score(existing)
    if computed is not None:
        return computed

    score = _tlp_first_score(
        _tlp_get(session_state, "execution_confidence"),
        _tlp_get(session_state, "execution_confidence_score"),
        _tlp_get(session_state, "trade_command_confidence"),
        getattr(trade, "confidence_score", None),
    )
    if score is not None and not _tlp_is_placeholder_execution_score(score):
        return score

    return None


def run_shared_trade_lifecycle_engines(
    session_state: Optional[Dict[str, Any]] = None,
    trade: Any = None,
    *,
    overwrite: bool = False,
    save: bool = True,
) -> TradeLifecyclePacket:
    """Run backend lifecycle engines and enrich the one canonical packet.

    This lets the Decision Center populate missing stage metrics without
    requiring the user to manually visit every page first. The approval
    calculates Commander Jimmy approval readiness from the canonical approval
    checklist.
    """
    ss = session_state if session_state is not None else _streamlit_session_state()
    packet = TradeLifecyclePacket.from_session(ss)

    symbol = _tlp_infer_symbol(packet, ss, trade)
    strategy = _tlp_infer_strategy(packet, ss, trade)
    mission = str(packet.identity.mission or getattr(trade, "mission", "") or "").strip()
    market_bias = str(packet.identity.market_bias or getattr(trade, "market_bias", "") or "").strip()
    stock_price = _tlp_float(packet.identity.stock_price or getattr(trade, "stock_price", 0.0), 0.0) or None

    opportunity_score = _tlp_infer_opportunity_score(packet, ss, symbol)
    construction_score = _tlp_infer_construction_score(packet, ss, trade, opportunity_score, strategy)
    execution_score = _tlp_infer_execution_score(packet, ss, trade, construction_score)
    approval_score = _tlp_approval_checklist_score(packet)

    updates: Dict[str, Any] = {
        "identity": {
            "symbol": symbol or None,
            "asset_class": packet.identity.asset_class or "Options",
            "strategy": strategy or None,
            "mission": mission or None,
            "market_bias": market_bias or None,
            "stock_price": stock_price,
        },
        "opportunity": {},
        "construction": {},
        "execution": {},
        "approval": {"score": approval_score},
        "status": "APPROVED" if packet.approval.approved else (packet.status or "DRAFT"),
    }

    if opportunity_score is not None and (overwrite or packet.opportunity.institutional_score is None):
        updates["opportunity"].update({
            "institutional_score": opportunity_score,
            "confidence": packet.opportunity.confidence if packet.opportunity.confidence is not None else opportunity_score,
            "summary": packet.opportunity.summary or "Computed by Shared Lifecycle Engine.",
        })

    if construction_score is not None and (overwrite or packet.construction.options_quality is None):
        updates["construction"].update({
            "strategy_type": strategy or packet.construction.strategy_type,
            "options_quality": construction_score,
        })

    if execution_score is not None and (
        overwrite
        or packet.execution.execution_confidence is None
        or _tlp_is_placeholder_execution_score(packet.execution.execution_confidence)
    ):
        updates["execution"].update({
            "execution_confidence": execution_score,
            "approval": packet.execution.approval or getattr(trade, "approval_status", None),
        })

    packet.merge_update(updates, source="Shared Lifecycle Engine", overwrite=overwrite)
    if packet.approval.approved:
        packet.status = "APPROVED"
    elif not packet.status:
        packet.status = "DRAFT"

    if packet.opportunity.institutional_score is not None:
        packet.mark_stage_complete(TradeStage.OPPORTUNITY_ANALYSIS, source="Shared Lifecycle Engine")
    if packet.construction.options_quality is not None:
        packet.mark_stage_complete(TradeStage.TRADE_CONSTRUCTION, source="Shared Lifecycle Engine")
    if packet.execution.execution_confidence is not None:
        packet.mark_stage_complete(TradeStage.EXECUTION_REVIEW, source="Shared Lifecycle Engine")

    if save:
        packet.save_to_session(ss)
    return packet

def _streamlit_session_state() -> Dict[str, Any]:
    try:
        import streamlit as st  # type: ignore
        return st.session_state
    except Exception:
        return {}


# Backward-compatible aliases for old imports.
DecisionPacket = TradeLifecyclePacket
OpportunityPacket = TradeLifecyclePacket
OptionsPacket = TradeLifecyclePacket


def get_trade_lifecycle_packet(session_state: Optional[Dict[str, Any]] = None) -> TradeLifecyclePacket:
    return TradeLifecyclePacket.from_session(session_state)


def save_trade_lifecycle_packet(packet: TradeLifecyclePacket, session_state: Optional[Dict[str, Any]] = None) -> TradeLifecyclePacket:
    return packet.save_to_session(session_state)


def create_or_load_packet(
    symbol: Optional[str] = None,
    source: Optional[str] = None,
    session_state: Optional[Dict[str, Any]] = None,
) -> TradeLifecyclePacket:
    packet = TradeLifecyclePacket.from_session(session_state)
    if symbol and not packet.identity.symbol:
        packet.identity.symbol = symbol
    if source:
        packet.metadata.last_source = source
        packet.identity.source = packet.identity.source or source
    return packet


def render_stage_value(packet: TradeLifecyclePacket, stage: TradeStage) -> str:
    return packet.stage_display(stage)
