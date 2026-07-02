import streamlit as st
import html
import textwrap

try:
    from options_engine.trade_lifecycle_packet import TradeLifecyclePacket, TradeStage, run_shared_trade_lifecycle_engines
except Exception:
    TradeLifecyclePacket = None
    TradeStage = None
    run_shared_trade_lifecycle_engines = None
from datetime import date, datetime, timezone

from options_engine.constants import (
    PAGE_TITLE,
    PAGE_ICON,
    APPROVAL_OPTIONS,
    PENDING_TEXT,
)
from options_engine.registry.strategy_registry import STRATEGY_REGISTRY
from options_engine.state.trade_state import get_trade
from options_engine.ui.ui_helpers import (
    section_header,
    status_pill,
    strategy_card,
)
from options_engine.calculators import calculate_trade
from options_engine.recommendation_engine import recommend_strategy
from options_engine.validators import validate_trade, get_validation_checks
from options_engine.approval_engine import approve_trade, approval_reason
from options_engine.execution_ticket import build_execution_ticket
from options_engine.decision_packet import (
    clear_packet_from_session,
)


st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
)


# ============================================================
# Utility Helpers
# ============================================================

def money(value: float) -> str:
    return f"${value:,.2f}"


def percent(value: float) -> str:
    return f"{value:,.2f}%"


def score_label(value: float | int | None, waiting_text: str = "Waiting...") -> str:
    try:
        number = float(value) if value is not None else 0.0
    except Exception:
        number = 0.0
    return f"{number:,.1f}" if number > 0 else waiting_text


def trace_packet(stage: str, packet) -> None:
    """No-op trace hook retained for local debugging compatibility."""
    return


def resolve_packet_scores(packet) -> dict:
    """Resolve stage-aware scores from the canonical TradeLifecyclePacket only."""
    if TradeLifecyclePacket is None or not isinstance(packet, TradeLifecyclePacket):
        return {
            "opportunity_score": 0.0,
            "options_quality_score": 0.0,
            "execution_confidence": 0.0,
            "opportunity_label": "Waiting for Options Center...",
            "construction_label": "Waiting for Options Center...",
            "execution_label": "Waiting for Options Decision Center...",
        }

    opportunity_score = float(packet.opportunity.institutional_score or 0.0)
    options_quality_score = float(packet.construction.options_quality or 0.0)
    execution_confidence = float(packet.execution.execution_confidence or 0.0)

    return {
        "opportunity_score": opportunity_score,
        "options_quality_score": options_quality_score,
        "execution_confidence": execution_confidence,
        "opportunity_label": score_label(opportunity_score or options_quality_score, "Waiting for Options Center..."),
        "construction_label": score_label(options_quality_score, "Waiting for Options Center..."),
        "execution_label": score_label(execution_confidence, "Waiting for Options Decision Center..."),
    }


def is_placeholder_decision_score(value) -> bool:
    try:
        return abs(float(value) - 35.0) < 0.0001
    except Exception:
        return False


def compute_decision_readiness_score(trade, packet=None) -> float:
    """Checklist-based Decision Readiness score for Options Decision Center.

    Replaces the old placeholder 35 with a score that reflects how much of the
    approval workflow is actually complete.
    """
    score = 0.0
    max_score = 0.0

    def add(weight: float, passed: bool) -> None:
        nonlocal score, max_score
        max_score += float(weight)
        if passed:
            score += float(weight)

    symbol = str(getattr(trade, "symbol", "") or getattr(packet, "symbol", "") or "").strip()
    strategy = str(
        (trade.active_strategy() if hasattr(trade, "active_strategy") else "")
        or getattr(trade, "recommended_strategy", "")
        or getattr(packet, "recommended_strategy", "")
        or ""
    ).strip()

    opportunity_score = 0.0
    construction_score = 0.0
    if isinstance(packet, TradeLifecyclePacket):
        opportunity_score = float(packet.opportunity.institutional_score or 0.0)
        construction_score = float(packet.construction.options_quality or 0.0)

    add(8, bool(symbol))
    add(10, bool(strategy) and strategy not in {"Pending", "No Options Trade", "No options structure", "No New Long Premium"})
    add(12, opportunity_score >= 60)
    add(18, construction_score >= 60)

    try:
        checked_trade = validate_trade(trade)
        checks = get_validation_checks(checked_trade)
    except Exception:
        checked_trade = trade
        checks = {}

    def check_pass(name: str) -> bool:
        try:
            status = str((checks.get(name) or ("", ""))[0]).upper().strip()
            return status in {"PASS", "OK", "APPROVED"} or "PASS" in status
        except Exception:
            return False

    add(8, check_pass("Premium") or float(getattr(trade, "premium", 0.0) or 0.0) > 0)
    add(8, check_pass("Position Size") or int(getattr(trade, "contracts", 0) or 0) >= 1)
    add(10, check_pass("Buying Power"))
    add(8, check_pass("Expiration"))
    add(6, check_pass("Breakeven vs Stock"))

    approval_status = str(getattr(checked_trade, "approval_status", "") or "").upper().strip()
    validation_status = str(getattr(checked_trade, "validation_status", "") or "").upper().strip()
    construction_complete = bool(getattr(checked_trade, "construction_complete", False))

    add(6, validation_status in {"PASS", "OK", "APPROVED"} or "PASS" in validation_status)
    add(6, construction_complete or "APPROVED" in approval_status)

    try:
        approved_trade = approve_trade(checked_trade)
        approval_status = str(getattr(approved_trade, "approval_status", "") or approval_status).upper().strip()
    except Exception:
        approved_trade = checked_trade

    add(6, "REJECT" not in approval_status and "FAIL" not in validation_status)

    if max_score <= 0:
        return 0.0
    return max(0.0, min(100.0, round((score / max_score) * 100.0, 1)))


def decision_readiness_label(score: float) -> str:
    if score >= 85:
        return "🟢 READY"
    if score >= 65:
        return "🟡 REVIEW"
    if score > 0:
        return "🔴 NOT READY"
    return "Pending"


def responsive_block_start(class_names: str) -> None:
    st.markdown(f'<div class="{class_names}">', unsafe_allow_html=True)


def responsive_block_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_step_separator() -> None:
    st.markdown('<div class="otcc-step-divider"></div>', unsafe_allow_html=True)


def _compact_panel_value(value) -> str:
    text = str(value if value is not None else "Pending")
    return html.escape(text)


def render_compact_metric_panel(items: list[tuple[str, str]], columns: int = 4) -> None:
    cols = max(1, int(columns or 1))
    cells = []
    for label, value in items:
        cells.append(
            f"""
            <div class="otcc-cmetric-item">
                <div class="otcc-cmetric-label">{html.escape(str(label))}</div>
                <div class="otcc-cmetric-value">{_compact_panel_value(value)}</div>
            </div>
            """
        )

    markup = textwrap.dedent(
        f"""
        <div class="otcc-cmetric-grid" style="grid-template-columns: repeat({cols}, minmax(0, 1fr));">
            {''.join(cells)}
        </div>
        """
    ).strip()
    st.markdown(markup, unsafe_allow_html=True)


def render_native_metric_grid(items: list[tuple[str, str]], columns: int = 4, block_class: str = "otcc-grid-4") -> None:
    cols = max(1, int(columns or 1))
    responsive_block_start(block_class)
    column_group = st.columns(cols)
    for idx, (label, value) in enumerate(items):
        with column_group[idx % cols]:
            st.metric(label, value)
    responsive_block_end()


# ============================================================
# Institutional Review Helpers
# ============================================================

def packet_is_approved(packet) -> bool:
    try:
        return bool(getattr(getattr(packet, "approval", None), "approved", False)) or str(getattr(packet, "status", "")).upper() == "APPROVED"
    except Exception:
        return False


def approval_bool(value) -> bool:
    return bool(value)


def approval_percent(packet, trade=None) -> float:
    try:
        packet_score = float(getattr(getattr(packet, "approval", None), "score", 0.0) or 0.0)
    except Exception:
        packet_score = 0.0
    if packet_score > 0:
        return max(0.0, min(100.0, packet_score))
    try:
        return compute_decision_readiness_score(trade, packet) if trade is not None else 0.0
    except Exception:
        return 0.0


def approval_checklist_from_trade(trade, packet=None) -> dict:
    """Infer the institutional approval checklist from the canonical packet + current trade."""
    try:
        checked_trade = validate_trade(trade)
        checks = get_validation_checks(checked_trade)
    except Exception:
        checked_trade = trade
        checks = {}

    def check_pass(name: str) -> bool:
        try:
            status = str((checks.get(name) or ("", ""))[0]).upper().strip()
            return status in {"PASS", "OK", "APPROVED"} or "PASS" in status or "APPROVED" in status
        except Exception:
            return False

    opportunity_score = 0.0
    construction_score = 0.0
    if isinstance(packet, TradeLifecyclePacket):
        opportunity_score = float(packet.opportunity.institutional_score or 0.0)
        construction_score = float(packet.construction.options_quality or 0.0)

    strategy = str(
        (trade.active_strategy() if hasattr(trade, "active_strategy") else "")
        or getattr(trade, "recommended_strategy", "")
        or getattr(packet, "recommended_strategy", "")
        or ""
    ).strip()

    premium = float(getattr(trade, "premium", 0.0) or 0.0)
    long_premium = float(getattr(trade, "long_premium", 0.0) or 0.0)
    strike = float(getattr(trade, "strike", 0.0) or 0.0)
    expiration = getattr(trade, "expiration", None)
    contracts = int(getattr(trade, "contracts", 0) or 0)
    buying_power = float(getattr(trade, "buying_power", 0.0) or 0.0)
    buying_power_required = float(getattr(trade, "buying_power_required", 0.0) or 0.0)
    max_profit = float(getattr(trade, "max_profit", 0.0) or 0.0)
    max_loss = float(getattr(trade, "max_loss", 0.0) or 0.0)
    reward_risk = float(getattr(trade, "reward_risk_ratio", 0.0) or 0.0)

    return {
        "trend_confirmed": bool(strategy) and strategy not in {"Pending", "No Options Trade", "No options structure", "No New Long Premium"} and (opportunity_score >= 60 or construction_score >= 60),
        "premium_confirmed": check_pass("Premium") or premium > 0 or long_premium > 0,
        "liquidity_confirmed": construction_score >= 60,
        "strike_confirmed": strike > 0,
        "expiration_confirmed": check_pass("Expiration") or expiration is not None,
        "position_size_confirmed": check_pass("Position Size") or contracts >= 1,
        "buying_power_confirmed": check_pass("Buying Power") or buying_power <= 0 or buying_power_required <= 0 or buying_power_required <= buying_power,
        "event_risk_confirmed": True,
        "risk_reward_confirmed": check_pass("Breakeven vs Stock") or reward_risk > 0 or max_profit > 0 or max_loss > 0,
    }


def institutional_review_checks(trade, packet=None) -> dict:
    """Return check values + reasons, auto-evaluating objective checks."""
    checks = approval_checklist_from_trade(trade, packet)
    strike = float(getattr(trade, "strike", 0.0) or 0.0)
    premium = float(getattr(trade, "premium", 0.0) or 0.0)
    contracts = int(getattr(trade, "contracts", 0) or 0)
    buying_power = float(getattr(trade, "buying_power", 0.0) or 0.0)
    buying_power_required = float(getattr(trade, "buying_power_required", 0.0) or 0.0)
    expiration = getattr(trade, "expiration", None)
    construction_score = float(getattr(getattr(packet, "construction", None), "options_quality", 0.0) or 0.0)

    reasons = {
        "trend_confirmed": "Trend/strategy alignment is missing.",
        "premium_confirmed": "Premium must be entered and greater than zero.",
        "liquidity_confirmed": "Construction quality below liquidity threshold (60).",
        "strike_confirmed": "Short strike must be greater than zero.",
        "expiration_confirmed": "Expiration date must be in the future.",
        "position_size_confirmed": "Contracts must be at least 1.",
        "buying_power_confirmed": "Required buying power exceeds available buying power.",
        "event_risk_confirmed": "Event risk requires manual confirmation.",
        "risk_reward_confirmed": "Risk / Reward requires manual review confirmation.",
    }

    auto = {
        "trend_confirmed": True,
        "premium_confirmed": True,
        "liquidity_confirmed": True,
        "strike_confirmed": True,
        "expiration_confirmed": True,
        "position_size_confirmed": True,
        "buying_power_confirmed": True,
        "event_risk_confirmed": False,
        "risk_reward_confirmed": False,
    }

    values = {
        "trend_confirmed": bool(checks.get("trend_confirmed", False)),
        "premium_confirmed": bool(checks.get("premium_confirmed", premium > 0)),
        "liquidity_confirmed": bool(checks.get("liquidity_confirmed", construction_score >= 60)),
        "strike_confirmed": bool(checks.get("strike_confirmed", strike > 0)),
        "expiration_confirmed": bool(checks.get("expiration_confirmed", expiration is not None and expiration > date.today())),
        "position_size_confirmed": bool(checks.get("position_size_confirmed", contracts >= 1)),
        "buying_power_confirmed": bool(checks.get("buying_power_confirmed", buying_power <= 0 or buying_power_required <= 0 or buying_power_required <= buying_power)),
        "event_risk_confirmed": bool(getattr(getattr(packet, "approval", None), "event_risk_confirmed", False)),
        "risk_reward_confirmed": bool(getattr(getattr(packet, "approval", None), "risk_reward_confirmed", False)),
    }

    return {
        key: {
            "value": values[key],
            "auto": auto[key],
            "reason": "" if values[key] else reasons[key],
        }
        for key in values
    }


def render_workflow_progress(trade, packet=None) -> None:
    """Institutional workflow timeline shown below Mission Briefing."""
    mission_done = bool(getattr(packet, "symbol", "") or getattr(trade, "symbol", ""))
    recommendation_done = bool(getattr(packet, "recommended_strategy", "") or trade.active_strategy() or getattr(trade, "recommended_strategy", ""))
    review_score = float(getattr(getattr(packet, "approval", None), "score", 0.0) or 0.0)
    review_done = review_score >= 75.0
    review_partial = review_score > 0.0 and not review_done
    construction_done = bool(getattr(trade, "construction_complete", False) or getattr(getattr(packet, "construction", None), "completed", False))
    validation_status = str(getattr(trade, "validation_status", "") or "").upper().strip()
    validation_done = validation_status not in {"", "PENDING"}
    approval_done = bool(getattr(getattr(packet, "approval", None), "approved", False)) or str(getattr(packet, "status", "")).upper() == "APPROVED"
    completed_stages = list(getattr(getattr(packet, "metadata", None), "completed_stages", []) or [])
    order = getattr(packet, "order", None)
    execution_handoff = bool(
        approval_done
        and (
            "ORDER_EXECUTION" in completed_stages
            or bool(getattr(order, "completed", False))
            or bool(getattr(order, "order_id", ""))
            or bool(getattr(order, "submitted_at", ""))
            or str(getattr(order, "status", "") or "").upper() in {"SENT", "SUBMITTED", "FILLED", "PARTIAL"}
        )
    )
    execution_partial = bool(approval_done and not execution_handoff)

    stage_labels = [
        "Mission Briefing",
        "Recommendation",
        "Institutional Review",
        "Construction",
        "Validation",
        "Approval",
        "Execution",
    ]

    if execution_handoff:
        states = ["complete"] * len(stage_labels)
    else:
        if approval_done:
            active_index = 6
        elif validation_done:
            active_index = 5
        elif construction_done:
            active_index = 4
        elif review_done:
            active_index = 3
        elif review_partial:
            active_index = 2
        elif recommendation_done:
            active_index = 2
        elif mission_done:
            active_index = 1
        else:
            active_index = 0

        states = []
        for idx, _ in enumerate(stage_labels):
            if idx < active_index:
                states.append("complete")
            elif idx == active_index:
                states.append("current")
            else:
                states.append("pending")

    node_html = []
    for idx, label in enumerate(stage_labels, start=1):
        state = states[idx - 1]
        symbol = "✓" if state == "complete" else str(idx)
        line_state = "complete" if idx < len(stage_labels) and states[idx - 1] == "complete" else "pending"
        node_html.append(
            f"""
            <div class="otcc-timeline-stage otcc-stage-{state}">
                <div class="otcc-timeline-circle">{symbol}</div>
                <div class="otcc-timeline-label">{label}</div>
            </div>
            {"<div class='otcc-timeline-connector otcc-line-" + line_state + "'></div>" if idx < len(stage_labels) else ""}
            """
        )

    with st.container(border=True):
        st.markdown("### Workflow Progress")
        st.markdown(
            f"""
            <div class="otcc-timeline-wrap">
                {''.join(node_html)}
            </div>
            """,
            unsafe_allow_html=True,
        )


def sync_approval_review_to_lifecycle(trade, packet=None, *, overwrite_checks: bool = True):
    """Write OP2 approval readiness into the canonical TradeLifecyclePacket."""
    if TradeLifecyclePacket is None:
        return packet

    if not isinstance(packet, TradeLifecyclePacket):
        packet = TradeLifecyclePacket.from_session(st.session_state)

    checklist = approval_checklist_from_trade(trade, packet)
    completed = sum(1 for value in checklist.values() if bool(value))
    total = max(len(checklist), 1)
    score = round((completed / total) * 100.0, 1)

    approval_updates = {"score": score}
    if overwrite_checks:
        approval_updates.update(checklist)

    packet.merge_update({"approval": approval_updates}, source="Options Decision Center", overwrite=True)
    if getattr(packet.approval, "approved", False):
        packet.status = "APPROVED"
    elif not str(getattr(packet, "status", "")).upper() == "APPROVED":
        packet.status = "DRAFT"
    packet.save_to_session(st.session_state)
    return packet


def approve_packet_in_lifecycle(trade, packet=None):
    if TradeLifecyclePacket is None:
        return packet
    if not isinstance(packet, TradeLifecyclePacket):
        packet = TradeLifecyclePacket.from_session(st.session_state)
    packet = sync_approval_review_to_lifecycle(trade, packet, overwrite_checks=True)
    packet.approval.approved = True
    packet.approval.approved_by = "Trade Review Desk"
    packet.approval.approved_timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    packet.approval.notes = packet.approval.notes or "Approved in Options Decision Center."
    packet.status = "APPROVED"
    packet.save_to_session(st.session_state)
    try:
        trade.approval_status = "APPROVED"
    except Exception:
        pass
    return packet


def clear_packet_approval(trade, packet=None):
    if TradeLifecyclePacket is None:
        return packet
    if not isinstance(packet, TradeLifecyclePacket):
        packet = TradeLifecyclePacket.from_session(st.session_state)
    packet.approval.approved = False
    packet.approval.approved_by = ""
    packet.approval.approved_timestamp = ""
    packet.approval.notes = "Approval cleared; trade reopened for editing."
    packet.status = "DRAFT"
    packet.save_to_session(st.session_state)
    try:
        trade.approval_status = PENDING_TEXT
        trade.reset_validation()
    except Exception:
        pass
    return packet


def render_commander_approval(trade, packet=None):
    section_header(
        "Step 3",
        "Institutional Review",
        "Validate the proposed trade against institutional quality standards before construction is finalized.",
    )

    if TradeLifecyclePacket is None:
        st.warning("Lifecycle packet engine unavailable.")
        return packet

    if not isinstance(packet, TradeLifecyclePacket):
        packet = TradeLifecyclePacket.from_session(st.session_state)

    approval = getattr(packet, "approval", None)
    if approval is None:
        st.warning("Approval section unavailable in packet.")
        return packet

    checklist_fields = [
        ("trend_confirmed", "Trend confirmed"),
        ("premium_confirmed", "Premium acceptable"),
        ("liquidity_confirmed", "Liquidity acceptable"),
        ("strike_confirmed", "Strike approved"),
        ("expiration_confirmed", "Expiration approved"),
        ("position_size_confirmed", "Position size approved"),
        ("buying_power_confirmed", "Buying power verified"),
        ("event_risk_confirmed", "Event risk checked"),
        ("risk_reward_confirmed", "Risk / Reward approved"),
    ]
    changed = False
    check_meta = institutional_review_checks(trade, packet)

    with st.container(border=True):
        st.markdown(
            """
            <div class="otcc-approval-card">
                <div class="otcc-approval-title">Institutional Review Dashboard</div>
                <div class="otcc-approval-subtitle">Reviewed by Trade Review Desk</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        left, right = st.columns([1.2, 1.0])

        with left:
            st.markdown("### Institutional Checklist")
            responsive_block_start("otcc-grid-3 otcc-checklist-grid otcc-checklist-compact")
            cols = st.columns(3)
            for index, (key, label) in enumerate(checklist_fields):
                with cols[index % 3]:
                    current = bool(getattr(approval, key, False))
                    auto_check = bool(check_meta.get(key, {}).get("auto", False))
                    desired = bool(check_meta.get(key, {}).get("value", current))
                    if auto_check:
                        if current != desired:
                            setattr(approval, key, desired)
                            changed = True
                        st.checkbox(label, value=desired, key=f"otcc_approval_check_{key}", disabled=True)
                        if not desired:
                            st.caption(f"❌ {check_meta.get(key, {}).get('reason', '')}")
                    else:
                        new_value = st.checkbox(label, value=current, key=f"otcc_approval_check_{key}")
                        if new_value != current:
                            setattr(approval, key, new_value)
                            changed = True
            responsive_block_end()

        completed = sum(1 for key, _ in checklist_fields if bool(getattr(approval, key, False)))
        total = 9
        score = round((completed / total) * 100.0, 1)
        if float(getattr(approval, "score", 0.0) or 0.0) != score:
            approval.score = score
            changed = True

        approved = bool(getattr(approval, "approved", False))
        status_text = "APPROVED" if approved else "DRAFT"
        if str(getattr(packet, "status", "DRAFT") or "DRAFT") != status_text:
            packet.status = status_text
            changed = True

        if changed:
            packet.save_to_session(st.session_state)

        if score >= 75.0:
            readiness_color = "#166534"
            readiness_label = "Green"
        elif score >= 50.0:
            readiness_color = "#92400e"
            readiness_label = "Yellow"
        else:
            readiness_color = "#991b1b"
            readiness_label = "Red"

        with left:
            st.markdown(
                f"""
                <div class="otcc-readiness-wrap">
                    <div class="otcc-readiness-label">Approval Readiness</div>
                    <div class="otcc-readiness-value">{score:,.1f}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.progress(min(max(score / 100.0, 0.0), 1.0))
            st.markdown(f"<span style='color:{readiness_color};font-weight:800;'>{readiness_label} readiness</span>", unsafe_allow_html=True)
        with right:
            st.markdown("### Institutional Decision")
            decision_rows = [
                ("Status", str(packet.status or "DRAFT")),
                ("Readiness", f"{score:,.1f}%"),
                ("Approved By", str(getattr(approval, "approved_by", "") or "Pending")),
                ("Timestamp", str(getattr(approval, "approved_timestamp", "") or "Pending")),
            ]
            st.markdown(
                "<div class='otcc-kv-card'>"
                + "".join(
                    f"<div class='otcc-kv-row'><div class='otcc-kv-key'>{key}</div><div class='otcc-kv-val'>{value}</div></div>"
                    for key, value in decision_rows
                )
                + "</div>",
                unsafe_allow_html=True,
            )

        if approved:
            approved_ts = str(getattr(approval, "approved_timestamp", "") or "")
            st.markdown(
                f"""
                <div class="otcc-approved-banner">
                    <div class="otcc-approved-banner-title">✅ APPROVED</div>
                    <div class="otcc-approved-banner-meta">
                        Trade Review Desk<br>
                        Trade Approved<br>
                        Packet Status: {packet.status or "APPROVED"}<br>
                        Timestamp: {approved_ts or "Pending"}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        responsive_block_start("otcc-actions-row")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Approve Trade", key="otcc_approve_trade_packet", use_container_width=True, type="primary", disabled=approved):
                if score < 75.0:
                    st.warning("Approval readiness must be at least 75% before this trade can be approved.")
                else:
                    approval.approved = True
                    approval.approved_by = "Trade Review Desk"
                    approval.approved_timestamp = datetime.now(timezone.utc).isoformat()
                    packet.status = "APPROVED"
                    packet.save_to_session(st.session_state)
                    st.rerun()
        with c2:
            if st.button("Clear Approval", key="otcc_clear_trade_approval", use_container_width=True, disabled=not approved):
                approval.approved = False
                approval.approved_by = ""
                approval.approved_timestamp = ""
                packet.status = "DRAFT"
                packet.save_to_session(st.session_state)
                st.rerun()
        responsive_block_end()

    return packet

def packet_source_display(packet) -> str:
    """Lifecycle owns the packet; modules are contributors, not sources."""
    return "Lifecycle Engine"


def packet_contributors_display(packet) -> str:
    if packet is None:
        return "Pending"
    try:
        label = packet.contributors_label()
        if label and label != "Pending":
            return label
    except Exception:
        pass

    contributors = []
    try:
        history = list(getattr(getattr(packet, "metadata", None), "history", []) or [])
    except Exception:
        history = []
    ignored = {
        "Lifecycle Engine",
        "Shared Lifecycle Engine",
        "legacy_session_import",
        "session_packet_reconcile",
        "symbol_stage_memory_save",
        "symbol_stage_memory_restore",
        "legacy_from_dict",
        "session_legacy",
    }
    for item in history:
        if not isinstance(item, dict):
            continue
        src = str(item.get("source") or "").strip()
        if src and src not in ignored and src not in contributors and not src.startswith("legacy_") and not src.startswith("session_"):
            contributors.append(src)
    return " / ".join(contributors) if contributors else "Pending"


def resolve_symbol_handoff(trade):
    possible_keys = [
        "option_symbol",
        "trade_command_symbol",
        "trade_symbol",
        "selected_symbol",
        "research_ticker",
        "scanner_selected_symbol",
        "opportunity_symbol",
        "active_symbol",
        "ticker",
    ]

    if trade.symbol:
        return trade.symbol

    for key in possible_keys:
        value = st.session_state.get(key)
        if isinstance(value, str) and value.strip():
            trade.symbol = value.strip().upper()
            return trade.symbol

    return trade.symbol


def inject_commander_css():
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1.35rem !important;
                padding-bottom: 2.4rem !important;
                max-width: 1700px !important;
                padding-left: clamp(0.9rem, 2.2vw, 2.75rem) !important;
                padding-right: clamp(0.9rem, 2.2vw, 2.75rem) !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }

            .block-container h1 {
                margin-bottom: 0.2rem;
                font-size: clamp(1.85rem, 3.5vw, 2.55rem) !important;
                font-weight: 900 !important;
                color: #1f2937 !important;
            }

            .block-container h2 {
                margin-top: 0.45rem;
                margin-bottom: 0.15rem;
                line-height: 1.15;
                font-size: clamp(1.12rem, 2.2vw, 1.50rem) !important;
                font-weight: 850 !important;
                color: #1f2937 !important;
            }

            .block-container h3 {
                font-size: clamp(1.0rem, 1.55vw, 1.22rem) !important;
                font-weight: 850 !important;
                color: #1f2937 !important;
            }

            .block-container p {
                margin-bottom: 0.35rem;
            }

            .block-container div[data-testid="stCaptionContainer"] {
                font-size: 0.84rem;
                line-height: 1.35;
            }

            div[data-testid="stVerticalBlockBorderWrapper"] {
                padding: 0.88rem 0.92rem;
                border-radius: 14px;
            }

            div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {
                gap: 0.26rem;
            }

            .otcc-step-divider {
                border-top: 1px solid rgba(148, 163, 184, 0.30);
                margin: 0.75rem 0 0.65rem 0;
            }

            div[data-testid="stVerticalBlock"] > div:has(> hr) {
                margin-top: 0.1rem;
                margin-bottom: 0.1rem;
            }

            div[data-testid="stAlert"] {
                padding-top: 0.45rem;
                padding-bottom: 0.45rem;
            }

            .otcc-commander-card {
                border: 1px solid rgba(148, 163, 184, 0.25);
                border-radius: 18px;
                padding: 0.9rem 1rem;
                margin-bottom: 0.55rem;
                background: linear-gradient(135deg, rgba(15, 23, 42, 0.06), rgba(30, 41, 59, 0.02));
            }

            .otcc-kicker {
                font-size: 0.78rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                color: #64748b;
                font-weight: 700;
                margin-bottom: 0.35rem;
            }

            .otcc-commander-title {
                font-size: 1.22rem;
                line-height: 1.2;
                font-weight: 800;
                margin-bottom: 0.2rem;
            }

            .otcc-commander-text {
                font-size: 0.9rem;
                color: #475569;
                line-height: 1.45;
            }

            .otcc-mission-selected {
                border: 2px solid #2563eb;
                border-radius: 14px;
                padding: 0.75rem 0.9rem;
                background: rgba(37, 99, 235, 0.08);
                margin-bottom: 0.65rem;
            }

            .otcc-mission-idle {
                border: 1px solid rgba(148, 163, 184, 0.28);
                border-radius: 14px;
                padding: 0.75rem 0.9rem;
                background: rgba(248, 250, 252, 0.35);
                margin-bottom: 0.65rem;
            }

            .otcc-mission-title {
                font-weight: 800;
                font-size: 0.95rem;
                margin-bottom: 0.2rem;
            }

            .otcc-mission-desc {
                font-size: 0.8rem;
                color: #64748b;
                line-height: 1.35;
                min-height: 1.9rem;
            }

            .otcc-briefing-card {
                border: 1px solid rgba(34, 197, 94, 0.35);
                border-radius: 18px;
                padding: 1rem 1.1rem;
                margin-bottom: 0.75rem;
                background: rgba(240, 253, 244, 0.72);
            }

            .otcc-briefing-title {
                font-size: 1.35rem;
                font-weight: 850;
                color: #166534;
                line-height: 1.15;
                margin-bottom: 0.2rem;
            }

            .otcc-briefing-meta {
                color: #334155;
                font-size: 0.9rem;
                line-height: 1.35;
            }

            .otcc-approval-card {
                border: 1px solid rgba(37, 99, 235, 0.28);
                border-radius: 18px;
                padding: 0.8rem 0.95rem;
                margin-bottom: 0.55rem;
                background: linear-gradient(135deg, rgba(219, 234, 254, 0.40), rgba(255, 255, 255, 0.92));
            }

            .otcc-approval-title {
                font-size: 1rem;
                font-weight: 850;
                color: #1e3a8a;
                margin-bottom: 0.25rem;
                line-height: 1.2;
            }

            .otcc-approval-subtitle {
                color: #334155;
                font-size: 0.86rem;
                margin-bottom: 0.2rem;
            }

            .otcc-approved-banner {
                border: 1px solid rgba(34, 197, 94, 0.45);
                border-radius: 14px;
                padding: 0.6rem 0.75rem;
                margin-top: 0.45rem;
                background: rgba(240, 253, 244, 0.9);
            }

            .otcc-approved-banner-title {
                color: #166534;
                font-size: 0.98rem;
                font-weight: 850;
                margin-bottom: 0.3rem;
            }

            .otcc-approved-banner-meta {
                color: #14532d;
                font-size: 0.86rem;
                line-height: 1.35;
            }

            .otcc-kv-card {
                border: 1px solid rgba(148, 163, 184, 0.30);
                border-radius: 12px;
                background: rgba(248, 250, 252, 0.78);
                padding: 0.55rem 0.7rem;
            }

            .otcc-kv-row {
                display: grid;
                grid-template-columns: minmax(110px, 140px) minmax(0, 1fr);
                gap: 0.65rem;
                padding: 0.3rem 0;
                border-bottom: 1px dashed rgba(148, 163, 184, 0.25);
                align-items: start;
            }

            .otcc-kv-row:last-child {
                border-bottom: none;
            }

            .otcc-kv-key {
                color: #475569;
                font-size: 0.8rem;
                font-weight: 700;
                line-height: 1.3;
            }

            .otcc-kv-val {
                color: #0f172a;
                font-size: 0.9rem;
                font-weight: 700;
                line-height: 1.35;
                word-break: break-word;
                overflow-wrap: anywhere;
            }

            .otcc-readiness-wrap {
                margin-top: 0.1rem;
                margin-bottom: 0.1rem;
            }

            .otcc-readiness-label {
                font-size: 0.8rem;
                color: #475569;
                font-weight: 700;
            }

            .otcc-readiness-value {
                font-size: 1.42rem;
                line-height: 1.08;
                font-weight: 800;
                color: #0f172a;
            }

            .otcc-timeline-wrap {
                display: flex;
                align-items: flex-start;
                gap: 0.25rem;
                flex-wrap: nowrap;
            }

            .otcc-timeline-stage {
                flex: 1 1 0;
                min-width: 110px;
                display: flex;
                flex-direction: column;
                align-items: center;
                text-align: center;
                gap: 0.4rem;
            }

            .otcc-timeline-circle {
                width: 2rem;
                height: 2rem;
                border-radius: 999px;
                border: 2px solid #cbd5e1;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.95rem;
                font-weight: 800;
                line-height: 1;
            }

            .otcc-stage-complete .otcc-timeline-circle {
                border-color: #16a34a;
                background: #16a34a;
                color: #ffffff;
            }

            .otcc-stage-current .otcc-timeline-circle {
                border-color: #2563eb;
                background: #2563eb;
                color: #ffffff;
            }

            .otcc-stage-pending .otcc-timeline-circle {
                border-color: #cbd5e1;
                background: #f1f5f9;
                color: #64748b;
            }

            .otcc-timeline-label {
                font-size: 0.68rem;
                font-weight: 700;
                color: #334155;
                line-height: 1.3;
                white-space: normal;
                overflow-wrap: anywhere;
            }

            .otcc-timeline-connector {
                flex: 0 0 clamp(12px, 1.5vw, 24px);
                height: 2rem;
                position: relative;
                margin-top: 0;
            }

            .otcc-timeline-connector::before {
                content: "";
                position: absolute;
                top: 50%;
                left: 0;
                right: 0;
                border-top: 2px solid #cbd5e1;
                transform: translateY(-50%);
            }

            .otcc-line-complete::before {
                border-top-color: #16a34a;
            }

            .otcc-main-two-col [data-testid="stHorizontalBlock"] {
                gap: 0.9rem;
            }

            .otcc-step23-row [data-testid="stHorizontalBlock"],
            .otcc-step67-row [data-testid="stHorizontalBlock"] {
                gap: 0.55rem;
                align-items: stretch;
            }

            .otcc-step4-row [data-testid="stHorizontalBlock"] {
                gap: 0.55rem;
            }

            .otcc-step4-row [data-testid="column"] {
                min-width: 0;
            }

            .otcc-step4-row [data-testid="stMetricLabel"] > div {
                font-size: 0.72rem !important;
                line-height: 1.2;
            }

            .otcc-step4-row [data-testid="stMetricValue"] > div,
            .otcc-step4-row div[data-testid="stMetricValue"] {
                font-size: clamp(0.8rem, 0.9vw, 0.94rem) !important;
                font-weight: 760;
                line-height: 1.05;
            }

            /* Strongly scoped overrides for Live Trade Math only */
            .otcc-live-math-panel div[data-testid="stMetricLabel"],
            .otcc-live-math-panel div[data-testid="stMetricLabel"] * {
                font-size: 0.72rem !important;
                line-height: 1.2 !important;
            }

            .otcc-live-math-panel div[data-testid="stMetricValue"],
            .otcc-live-math-panel div[data-testid="stMetricValue"] > div,
            .otcc-live-math-panel div[data-testid="stMetricValue"] p,
            .otcc-live-math-panel div[data-testid="stMetricValue"] span {
                font-size: 1.34rem !important;
                font-weight: 680 !important;
                line-height: 1.06 !important;
                letter-spacing: -0.01em;
            }

            div[data-testid="stMetricLabel"] {
                font-size: 0.74rem !important;
            }

            div[data-testid="stMetricValue"],
            div[data-testid="stMetricValue"] > div,
            div[data-testid="stMetricValue"] p,
            div[data-testid="stMetricValue"] span {
                font-size: 1.5rem !important;
                line-height: 1.08 !important;
                font-weight: 720 !important;
            }

            .otcc-step4-row [data-testid="stMarkdownContainer"] h3 {
                font-size: 0.9rem !important;
                margin-bottom: 0.2rem;
            }

            .otcc-step23-row [data-testid="column"],
            .otcc-step67-row [data-testid="column"] {
                min-width: 0;
            }

            .otcc-step23-row [data-testid="stVerticalBlock"],
            .otcc-step67-row [data-testid="stVerticalBlock"] {
                gap: 0.3rem;
            }

            .otcc-checklist-compact [data-testid="stCheckbox"] {
                margin-bottom: 0.08rem;
            }

            .otcc-checklist-compact [data-testid="stMarkdownContainer"] p {
                font-size: 0.82rem;
            }

            .otcc-checklist-compact [data-testid="stCaptionContainer"] {
                font-size: 0.74rem;
                line-height: 1.25;
            }

            .otcc-construction-card,
            .otcc-review-card,
            .otcc-compact-card {
                padding-top: 0.15rem;
            }

            .otcc-construction-card [data-testid="stMetricValue"] > div,
            .otcc-review-card [data-testid="stMetricValue"] > div,
            .otcc-compact-card [data-testid="stMetricValue"] > div {
                font-size: clamp(0.96rem, 1.1vw, 1.12rem);
                line-height: 1.1;
            }

            .otcc-construction-card div[data-testid="stMetricValue"],
            .otcc-review-card div[data-testid="stMetricValue"],
            .otcc-compact-card div[data-testid="stMetricValue"] {
                font-size: clamp(0.98rem, 1.12vw, 1.15rem) !important;
            }

            .otcc-construction-card [data-testid="stMetricLabel"] > div,
            .otcc-review-card [data-testid="stMetricLabel"] > div,
            .otcc-compact-card [data-testid="stMetricLabel"] > div {
                font-size: 0.74rem;
                font-weight: 650;
            }

            .otcc-cmetric-grid {
                display: grid;
                gap: 0.28rem 0.45rem;
                margin-top: 0.2rem;
                margin-bottom: 0.2rem;
            }

            .otcc-cmetric-item {
                min-width: 0;
                padding: 0.08rem 0;
            }

            .otcc-cmetric-label {
                font-size: 0.74rem;
                color: #475569;
                line-height: 1.2;
                margin-bottom: 0.1rem;
                white-space: normal;
                overflow: visible;
                text-overflow: clip;
            }

            .otcc-cmetric-value {
                font-size: 1rem;
                font-weight: 750;
                color: #111827;
                line-height: 1.15;
                white-space: normal;
                word-break: break-word;
                overflow-wrap: anywhere;
            }

            .otcc-status-card {
                border: 1px solid rgba(148, 163, 184, 0.30);
                border-radius: 8px;
                padding: 0.4rem 0.45rem;
                margin-bottom: 0.12rem;
                background: rgba(255, 255, 255, 0.70);
            }

            .otcc-status-title {
                font-size: 0.78rem;
                font-weight: 780;
                color: #1f2937;
                margin-bottom: 0.12rem;
            }

            .otcc-status-body {
                font-size: 0.82rem;
                color: #334155;
                line-height: 1.28;
            }

            .otcc-construction-card [data-testid="stMarkdownContainer"] h3,
            .otcc-review-card [data-testid="stMarkdownContainer"] h3,
            .otcc-compact-card [data-testid="stMarkdownContainer"] h3 {
                margin-top: 0.2rem;
                margin-bottom: 0.35rem;
            }

            .otcc-construction-card [data-testid="stVerticalBlock"],
            .otcc-review-card [data-testid="stVerticalBlock"],
            .otcc-compact-card [data-testid="stVerticalBlock"] {
                gap: 0.25rem;
            }

            .otcc-construction-card [data-testid="stButton"] {
                margin-top: 0.25rem;
            }

            [data-testid="stButton"] button,
            [data-testid="baseButton-secondary"],
            [data-testid="baseButton-primary"] {
                min-height: 2.35rem !important;
                padding-top: 0.22rem !important;
                padding-bottom: 0.22rem !important;
                font-size: 0.86rem !important;
                line-height: 1.2;
                border-radius: 10px !important;
            }

            .otcc-construction-card div[data-testid="stTextInput"],
            .otcc-construction-card div[data-testid="stNumberInput"],
            .otcc-construction-card div[data-testid="stDateInput"] {
                margin-bottom: 0.08rem;
            }

            .otcc-step4-row [data-baseweb="input"],
            .otcc-step4-row [data-baseweb="select"] {
                min-height: 1.9rem;
            }

            .otcc-step4-row [data-baseweb="input"] input,
            .otcc-step4-row [data-baseweb="select"] input {
                font-size: 0.82rem !important;
            }

            .otcc-construction-card [data-testid="stButton"] button {
                min-height: 2.0rem !important;
                font-size: 0.82rem !important;
            }

            [data-baseweb="input"] input,
            [data-baseweb="select"] input,
            [data-baseweb="textarea"] textarea {
                font-size: 0.9rem !important;
            }

            [data-baseweb="input"],
            [data-baseweb="select"] {
                min-height: 2.2rem;
            }

            [data-testid="stExpander"] details > summary {
                padding-top: 0.26rem;
                padding-bottom: 0.26rem;
                font-size: 0.84rem;
            }

            .otcc-compact-card [data-testid="stExpander"] {
                margin-top: 0.25rem;
            }

            .otcc-grid-4 [data-testid="stHorizontalBlock"],
            .otcc-grid-3 [data-testid="stHorizontalBlock"],
            .otcc-grid-2 [data-testid="stHorizontalBlock"],
            .otcc-actions-row [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap;
                gap: 0.8rem;
            }

            .otcc-grid-4 [data-testid="column"],
            .otcc-grid-3 [data-testid="column"],
            .otcc-grid-2 [data-testid="column"],
            .otcc-actions-row [data-testid="column"],
            .otcc-main-two-col [data-testid="column"] {
                min-width: 0;
            }

            div[data-testid="stMetricLabel"] > div,
            div[data-testid="stMetricValue"] > div {
                white-space: normal !important;
                overflow: visible !important;
                text-overflow: clip !important;
                overflow-wrap: anywhere;
                word-break: break-word;
            }

            div[data-testid="stMetricLabel"] {
                font-size: 0.74rem;
            }

            @media (max-width: 1440px) {
                .otcc-step23-row [data-testid="column"]:first-child {
                    flex: 0 0 44% !important;
                    width: 44% !important;
                }

                .otcc-step23-row [data-testid="column"]:last-child {
                    flex: 0 0 56% !important;
                    width: 56% !important;
                }

                .otcc-grid-4 [data-testid="column"] {
                    flex: 1 1 calc(50% - 0.65rem) !important;
                    width: calc(50% - 0.65rem) !important;
                }

                .otcc-briefing-title {
                    font-size: 1.2rem;
                }

                .otcc-cmetric-value {
                    font-size: 0.95rem;
                }
            }

            @media (max-width: 1280px) {
                .otcc-grid-3 [data-testid="column"] {
                    flex: 1 1 calc(50% - 0.65rem) !important;
                    width: calc(50% - 0.65rem) !important;
                }
            }

            @media (max-width: 1024px) {
                .otcc-timeline-wrap {
                    gap: 0.15rem;
                }

                .otcc-timeline-stage {
                    min-width: 98px;
                }

                div[data-testid="stMetricValue"] {
                    font-size: 1rem !important;
                }

                .otcc-grid-2 [data-testid="column"],
                .otcc-actions-row [data-testid="column"] {
                    flex: 1 1 calc(50% - 0.8rem) !important;
                    width: calc(50% - 0.8rem) !important;
                }

                .otcc-step23-row [data-testid="column"],
                .otcc-step4-row [data-testid="column"],
                .otcc-step67-row [data-testid="column"] {
                    flex: 1 1 100% !important;
                    width: 100% !important;
                }
            }

            @media (max-width: 768px) {
                .otcc-commander-title {
                    font-size: 1.02rem;
                }

                .otcc-briefing-title {
                    font-size: 1.04rem;
                }

                .otcc-approval-title {
                    font-size: 0.9rem;
                }

                .otcc-kv-row {
                    grid-template-columns: 1fr;
                    gap: 0.2rem;
                }

                .otcc-grid-4 [data-testid="column"],
                .otcc-grid-3 [data-testid="column"],
                .otcc-grid-2 [data-testid="column"],
                .otcc-actions-row [data-testid="column"] {
                    flex: 1 1 100% !important;
                    width: 100% !important;
                }

                .otcc-timeline-wrap {
                    flex-wrap: wrap;
                    row-gap: 0.65rem;
                }

                .otcc-timeline-stage {
                    flex: 1 1 calc(25% - 0.25rem);
                    min-width: 132px;
                }

                .otcc-timeline-connector {
                    display: none;
                }

                div[data-testid="stMetricValue"] {
                    font-size: 0.92rem !important;
                }

                .otcc-cmetric-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
                }

                .otcc-cmetric-value {
                    font-size: 0.88rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_commander_intro(trade):
    st.markdown(
        """
        <div class="otcc-commander-card">
            <div class="otcc-kicker">Strategy Desk · Options Decision Engine</div>
            <div class="otcc-commander-title">Define today’s options objective.</div>
            <div class="otcc-commander-text">
                Start with intent. The engine uses mission, symbol,
                market bias, and account context to guide construction.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    mission_options = [
        {
            "label": "Generate Income",
            "icon": "💰",
            "description": "Collect premium using income-focused option structures.",
        },
        {
            "label": "Buy Shares at a Discount",
            "icon": "🟢",
            "description": "Use options to potentially acquire stock below the current price.",
        },
        {
            "label": "Bullish Directional Trade",
            "icon": "📈",
            "description": "Express a bullish view with controlled risk and defined structure.",
        },
        {
            "label": "Protect Existing Shares",
            "icon": "🛡️",
            "description": "Reduce downside risk or generate income against an existing position.",
        },
        {
            "label": "High Probability Income",
            "icon": "🎯",
            "description": "Prioritize probability, discipline, and premium efficiency.",
        },
    ]

    responsive_block_start("otcc-grid-3")
    cols = st.columns(3)

    for index, mission in enumerate(mission_options):
        selected = trade.mission == mission["label"]
        css_class = "otcc-mission-selected" if selected else "otcc-mission-idle"

        with cols[index % 3]:
            st.markdown(
                f"""
                <div class="{css_class}">
                    <div class="otcc-mission-title">{mission['icon']} {mission['label']}</div>
                    <div class="otcc-mission-desc">{mission['description']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            button_label = "Selected Mission" if selected else "Choose Mission"
            if st.button(
                button_label,
                key=f"otcc_mission_card_{index}",
                use_container_width=True,
            ):
                trade.mission = mission["label"]
                trade.objective = mission["label"]
                trade.reset_validation()
                st.rerun()
    responsive_block_end()




def apply_trade_lifecycle_packet_to_trade(packet, trade) -> None:
    """Apply canonical packet fields to the local construction trade state."""
    if packet is None or trade is None:
        return
    if packet.identity.symbol:
        trade.symbol = packet.identity.symbol
    if packet.identity.strategy or packet.construction.strategy_type:
        trade.recommended_strategy = packet.construction.strategy_type or packet.identity.strategy
        trade.strategy = trade.strategy or trade.recommended_strategy
    if packet.opportunity.summary:
        trade.strategy_reason = packet.opportunity.summary
    if packet.construction.options_quality is not None:
        trade.strategy_confidence = float(packet.construction.options_quality or 0.0)
    else:
        # OP1-0701-H: Options Quality belongs to the construction stage.
        # Do not display an Opportunity score as Options Quality.
        trade.strategy_confidence = 0.0
    if packet.opportunity.approval:
        trade.institutional_grade = packet.opportunity.approval


def apply_decision_packet_if_needed(trade):
    # Canonical-only path: render KPIs from the shared lifecycle packet.
    # OP1-0701-H: run shared backend engines first so missing stage scores can
    # be populated without manually visiting every page.
    if TradeLifecyclePacket is not None:
        if run_shared_trade_lifecycle_engines is not None:
            canonical = run_shared_trade_lifecycle_engines(st.session_state, trade, overwrite=False, save=True)
        else:
            canonical = TradeLifecyclePacket.from_session(st.session_state)
        has_payload = bool(
            canonical.identity.symbol
            or canonical.opportunity.institutional_score is not None
            or canonical.construction.options_quality is not None
        )
        if has_payload:
            fingerprint = canonical.fingerprint()
            loaded = st.session_state.get("otcc_loaded_packet_fingerprint")
            if loaded != fingerprint:
                apply_trade_lifecycle_packet_to_trade(canonical, trade)
                st.session_state["otcc_loaded_packet_fingerprint"] = fingerprint
            return canonical
    return None


def sync_execution_review_to_lifecycle(trade, packet=None, *, resolve_confidence: bool = False):
    """Write Decision Center review output into canonical lifecycle packet."""
    if TradeLifecyclePacket is None or trade is None:
        return packet

    symbol = str(getattr(trade, "symbol", "") or st.session_state.get("selected_symbol") or "").upper().strip()
    if not symbol:
        return packet

    confidence = compute_decision_readiness_score(trade, packet)

    # OP1-0702-A: never preserve the old placeholder Decision Review score.
    # Decision Review now means checklist-based readiness.
    if confidence <= 0:
        existing = getattr(getattr(packet, "execution", None), "execution_confidence", None)
        if existing is not None and not is_placeholder_decision_score(existing):
            confidence = float(existing or 0.0)
    if confidence <= 0:
        return packet

    risk_per_trade = None
    account_size = float(getattr(trade, "account_size", 0.0) or 0.0)
    max_risk_allowed = float(getattr(trade, "max_risk_allowed", 0.0) or 0.0)
    if account_size > 0 and max_risk_allowed > 0:
        risk_per_trade = (max_risk_allowed / account_size) * 100.0

    if isinstance(packet, TradeLifecyclePacket):
        packet.merge_update(
            {
                "identity": {
                    "symbol": symbol,
                    "strategy": trade.active_strategy() or trade.recommended_strategy,
                },
                "execution": {
                    "execution_confidence": confidence,
                    "position_size": float(getattr(trade, "contracts", 0) or 0),
                    "account": str(getattr(trade, "account_type", "") or ""),
                    "risk_per_trade": risk_per_trade,
                    "approval": getattr(trade, "approval_status", None),
                },
            },
            source="Options Decision Center",
            overwrite=False,
        )
        if TradeStage is not None:
            packet.mark_stage_complete(TradeStage.EXECUTION_REVIEW, source="Options Decision Center")
        packet.save_to_session(st.session_state)
        return packet

    return TradeLifecyclePacket.update_execution_in_session(
        st.session_state,
        source="Options Decision Center",
        overwrite=False,
        symbol=symbol,
        strategy=trade.active_strategy() or trade.recommended_strategy,
        execution_confidence=confidence,
        position_size=float(getattr(trade, "contracts", 0) or 0),
        account=str(getattr(trade, "account_type", "") or ""),
        risk_per_trade=risk_per_trade,
        approval=getattr(trade, "approval_status", None),
    )

def render_opportunity_briefing(trade, packet):
    section_header(
        "Step 1",
        "Mission Briefing",
        "Opportunity context received from an upstream JFBP module.",
    )

    source = packet_source_display(packet) or "Lifecycle Engine"
    contributors = packet_contributors_display(packet)
    symbol = packet.symbol or trade.symbol or "Pending"
    strategy = packet.recommended_strategy or trade.recommended_strategy or trade.active_strategy() or "Pending"
    scores = resolve_packet_scores(packet)
    mission = trade.mission or packet.mission or "Pending"
    opportunity_grade = packet.opportunity_grade or "Pending"
    institutional_grade = packet.institutional_grade or trade.institutional_grade or "Pending"

    briefing_html = f"""
        <div class="otcc-briefing-card">
            <div class="otcc-kicker">Strategy Desk · Institutional Briefing Mode</div>
            <div class="otcc-briefing-title">Opportunity Received: {symbol} {strategy}</div>
            <div class="otcc-briefing-meta">
                Source: <strong>{source}</strong> · Contributors: <strong>{contributors}</strong> · Mission: <strong>{mission}</strong><br>
                Opportunity Grade: <strong>{opportunity_grade}</strong> ·
                Institutional Grade: <strong>{institutional_grade}</strong>
            </div>
        </div>
    """
    st.markdown(briefing_html, unsafe_allow_html=True)

    responsive_block_start("otcc-grid-3")
    score_cols = st.columns(3)
    score_cols[0].metric(
        "Options Opportunity",
        scores.get("opportunity_label") or score_label(scores["opportunity_score"], "Waiting for Options Center..."),
        help="Options opportunity score published by Options Center or preserved by the Lifecycle Engine.",
    )
    score_cols[1].metric(
        "Trade Construction",
        scores.get("construction_label") or score_label(scores["options_quality_score"], "Waiting for Options Trade Construction Center..."),
        help="Options quality from Options Center / Trade Construction. Waiting until computed.",
    )
    score_cols[2].metric(
        "Decision Readiness",
        scores.get("execution_label") or score_label(scores["execution_confidence"], "Waiting for Options Decision Center..."),
        help="Checklist-based readiness after Options Decision Center validation and approval.",
    )
    responsive_block_end()

    st.info(
        "The opportunity has been identified and the recommended strategy has been generated. "
        "Complete the institutional review, validate the trade structure, and confirm execution readiness before approving the trade."
    )

    responsive_block_start("otcc-grid-2")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Construct Received Opportunity", key="otcc_construct_packet", use_container_width=True):
            trade.user_selected_strategy = strategy if strategy != "Pending" else trade.user_selected_strategy
            trade.strategy = trade.user_selected_strategy or trade.recommended_strategy
            trade.construction_complete = False
            trade.approval_status = PENDING_TEXT
            st.rerun()

    with c2:
        if st.button("Clear Briefing / Use Discovery Mode", key="otcc_clear_packet", use_container_width=True):
            clear_packet_from_session(st.session_state)
            st.session_state.pop("trade_lifecycle_packet", None)
            st.rerun()
    responsive_block_end()

    with st.expander("Briefing packet details", expanded=False):
        st.json(packet.to_dict())


def render_other_strategy_selection(trade):
    with st.expander("Choose a different strategy", expanded=False):
        strategy_items = list(STRATEGY_REGISTRY.items())
        responsive_block_start("otcc-grid-2")
        rows = [st.columns(2), st.columns(2)]

        for idx, (key, strategy) in enumerate(strategy_items):
            row = rows[idx // 2]
            col = row[idx % 2]

            with col:
                selected = trade.active_strategy() == key
                if strategy_card(key, strategy, selected=selected):
                    trade.user_selected_strategy = key
                    trade.strategy = key
                    trade.construction_complete = False
                    trade.approval_status = PENDING_TEXT
                    trade.reset_results()
                    trade.reset_validation()
                    st.rerun()
        responsive_block_end()


# ============================================================
# Step 1 — Commander / Mission
# ============================================================

def render_opportunity_selection(trade):
    section_header(
        "Step 1",
        "Trade Briefing",
        "Define the mission, confirm the symbol, and give the engine basic context.",
    )

    resolve_symbol_handoff(trade)
    render_commander_intro(trade)
    recommend_strategy(trade)

    responsive_block_start("otcc-grid-3")
    col1, col2, col3 = st.columns(3)

    with col1:
        trade.symbol = st.text_input(
            "Which company are we discussing?",
            value=trade.symbol,
            placeholder="Example: AAPL",
            key="otcc_symbol",
        ).upper().strip()

        trade.market_bias = st.selectbox(
            "Market Bias",
            ["", "Bullish", "Neutral", "Bearish"],
            index=["", "Bullish", "Neutral", "Bearish"].index(trade.market_bias)
            if trade.market_bias in ["", "Bullish", "Neutral", "Bearish"]
            else 0,
            key="otcc_market_bias",
        )

    with col2:
        trade.stock_price = st.number_input(
            "Current Stock Price",
            min_value=0.0,
            value=float(trade.stock_price or 0.0),
            step=0.01,
            key="otcc_stock_price",
        )

        trade.account_size = st.number_input(
            "Account Size",
            min_value=0.0,
            value=float(trade.account_size or 0.0),
            step=1000.0,
            key="otcc_account_size",
        )

    with col3:
        trade.buying_power = st.number_input(
            "Available Buying Power",
            min_value=0.0,
            value=float(trade.buying_power or 0.0),
            step=1000.0,
            key="otcc_buying_power",
        )

        trade.max_risk_allowed = st.number_input(
            "Maximum Risk Allowed",
            min_value=0.0,
            value=float(trade.max_risk_allowed or 0.0),
            step=100.0,
            key="otcc_max_risk_allowed",
        )
    responsive_block_end()

    if trade.recommended_strategy:
        with st.container(border=True):
            st.markdown("### Strategy Recommendation")
            st.metric("Recommended Strategy", trade.recommended_strategy)
            st.metric("Options Quality", percent(trade.strategy_confidence))
            st.write(trade.strategy_reason)

            if st.button(
                "Use Recommendation",
                key="otcc_use_recommendation",
                use_container_width=True,
            ):
                trade.user_selected_strategy = trade.recommended_strategy
                trade.strategy = trade.recommended_strategy
                trade.construction_complete = False
                trade.approval_status = PENDING_TEXT
                trade.reset_results()
                trade.reset_validation()
                st.rerun()
    else:
        st.info("Choose a mission and symbol. The strategy desk will prepare the first recommendation.")


# ============================================================
# Step 2 — Strategy Selection
# ============================================================

def render_strategy_selection(trade, packet=None):
    locked = packet_is_approved(packet)
    section_header(
        "Step 2",
        "Strategy Recommendation",
        "Accept the recommended structure or deliberately choose a different one.",
    )

    if locked:
        st.info("This trade is approved. Clear Approval in Step 3 before changing the strategy.")

    if not trade.recommended_strategy:
        st.info("No recommendation yet. Complete the trade briefing first.")
        if not locked:
            render_other_strategy_selection(trade)
        else:
            st.caption("Strategy selection is locked because this packet is approved.")
        return

    with st.container(border=True):
        st.markdown("### Recommended Structure")
        responsive_block_start("otcc-grid-2")
        c1, c2 = st.columns(2)
        c1.metric("Strategy", trade.recommended_strategy)
        c2.metric("Options Quality", percent(trade.strategy_confidence) if float(trade.strategy_confidence or 0.0) > 0 else "Waiting for Options Center...")
        responsive_block_end()
        st.write(trade.strategy_reason or "Recommendation received from upstream context.")

        if st.button("Construct Recommended Trade", key="otcc_construct_recommended", use_container_width=True, disabled=locked):
            trade.user_selected_strategy = trade.recommended_strategy
            trade.strategy = trade.recommended_strategy
            trade.construction_complete = False
            trade.approval_status = PENDING_TEXT
            trade.reset_results()
            trade.reset_validation()
            st.rerun()

    if not locked:
        render_other_strategy_selection(trade)
    else:
        st.caption("Strategy selection is locked because this packet is approved.")

# ============================================================
# Step 4 — Trade Construction
# ============================================================

def render_trade_construction(trade, packet=None):
    strategy = trade.active_strategy()
    locked = bool(packet and getattr(getattr(packet, "approval", None), "approved", False))
    section_header(
        "Step 4",
        f"{strategy or 'Trade'} Construction",
        "Enter the trade structure. Cash-Secured Put math is live.",
    )

    if not strategy:
        st.warning("Accept the recommendation or select a strategy first.")
        return

    st.success(f"Selected Strategy: {strategy}")
    if locked:
        st.warning("🔒 Trade construction locked.")
        st.caption("Clear approval to modify this trade.")

    with st.container(border=True):
        responsive_block_start("otcc-construction-card")
        responsive_block_start("otcc-step4-row")
        left, right = st.columns([1.18, 0.92], gap="medium")

        with left:
            responsive_block_start("otcc-grid-3")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.text_input(
                    "Underlying",
                    value=trade.symbol,
                    key="otcc_construction_symbol_display",
                    disabled=True,
                )

                trade.expiration = st.date_input(
                    "Expiration",
                    value=trade.expiration or date.today(),
                    key="otcc_expiration",
                    disabled=locked,
                )

            with col2:
                trade.strike = st.number_input(
                    "Short Strike",
                    min_value=0.0,
                    value=float(trade.strike or 0.0),
                    step=0.5,
                    key="otcc_short_strike",
                    disabled=locked,
                )

                trade.long_strike = st.number_input(
                    "Long Strike / Protection Strike",
                    min_value=0.0,
                    value=float(trade.long_strike or 0.0),
                    step=0.5,
                    key="otcc_long_strike",
                    disabled=locked,
                )

            with col3:
                trade.premium = st.number_input(
                    "Short Premium",
                    min_value=0.0,
                    value=float(trade.premium or 0.0),
                    step=0.01,
                    key="otcc_short_premium",
                    disabled=locked,
                )

                trade.long_premium = st.number_input(
                    "Long Premium",
                    min_value=0.0,
                    value=float(trade.long_premium or 0.0),
                    step=0.01,
                    key="otcc_long_premium",
                    disabled=locked,
                )

                trade.contracts = st.number_input(
                    "Contracts",
                    min_value=1,
                    value=int(trade.contracts or 1),
                    step=1,
                    key="otcc_contracts",
                    disabled=locked,
                )
            responsive_block_end()

        trade = calculate_trade(trade)

        with right:
            responsive_block_start("otcc-live-math-panel")
            st.markdown("### Live Trade Math")
            responsive_block_start("otcc-grid-2")
            m1, m2 = st.columns(2)
            m3, m4 = st.columns(2)
            m5, m6 = st.columns(2)
            m7, m8 = st.columns(2)
            m9, m10 = st.columns(2)

            m1.metric("Credit", money(trade.credit))
            m2.metric("Debit", money(trade.debit))
            m3.metric("Buying Power Required", money(trade.buying_power_required))
            m4.metric("Max Profit", money(trade.max_profit))
            m5.metric("Max Loss", money(trade.max_loss))
            m6.metric("Breakeven", money(trade.breakeven))
            m7.metric("ROI", percent(trade.roi))
            m8.metric("Annualized Return", percent(trade.annualized_return))
            m9.metric("Reward / Risk", f"{trade.reward_risk_ratio:,.4f}")
            m10.metric("Contracts", int(trade.contracts or 0))
            responsive_block_end()
            responsive_block_end()

        responsive_block_end()

        if st.button("Mark Construction Complete", use_container_width=True, disabled=locked):
            trade.construction_complete = True
            trade.approval_status = "Pending validation"
            st.rerun()
        responsive_block_end()


# ============================================================
# Step 4 — Risk Validation
# ============================================================

def render_risk_validation(trade):
    section_header(
        "Step 5",
        "Risk Validation",
        "Validate objective constraints before approval.",
    )

    trade = validate_trade(trade)
    checks = get_validation_checks(trade)

    display_checks = {
        "Buying Power": checks["Buying Power"],
        "Expiration": checks["Expiration"],
        "Premium": checks["Premium"],
        "Position Size": checks["Position Size"],
        "Breakeven vs Stock": checks["Breakeven vs Stock"],
        "Overall Status": (trade.validation_status, "Aggregate validation result."),
    }

    with st.container(border=True):
        responsive_block_start("otcc-compact-card")
        responsive_block_start("otcc-grid-3")
        cols = st.columns(3)

        for index, (label, (status, message)) in enumerate(display_checks.items()):
            with cols[index % 3]:
                st.markdown(
                    f"""
                    <div class="otcc-status-card">
                        <div class="otcc-status-title">{html.escape(label)}</div>
                        <div class="otcc-status-body">{html.escape(str(status))} — {html.escape(str(message))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        responsive_block_end()
        responsive_block_end()

    if trade.warnings:
        with st.expander("Validation warnings", expanded=False):
            for warning in trade.warnings:
                st.warning(warning)

    if trade.validation_messages:
        with st.expander("Validation detail", expanded=False):
            for message in trade.validation_messages:
                st.write(f"• {message}")


# ============================================================
# Step 5 — Trade Approval
# ============================================================

def render_trade_approval(trade, packet=None):
    section_header(
        "Step 6",
        "Trade Approval",
        "Convert validation evidence into an approval decision.",
    )

    trade = approve_trade(trade)
    sync_execution_review_to_lifecycle(trade, packet)

    with st.container(border=True):
        responsive_block_start("otcc-compact-card")
        readiness_score = compute_decision_readiness_score(trade, packet)
        outstanding = 0
        if not trade.construction_complete:
            outstanding += 1
        outstanding += len(getattr(trade, "warnings", []) or [])

        st.markdown("### Institutional Decision")
        render_native_metric_grid(
            [
                ("Institutional Grade", trade.institutional_grade or "Pending"),
                ("Decision Readiness", f"{readiness_score:,.1f}%"),
                ("Approval Status", trade.approval_status or "WAIT"),
                ("Outstanding Issues", str(outstanding)),
            ],
            columns=4,
            block_class="otcc-grid-4",
        )

        if outstanding > 0:
            st.warning(f"Outstanding Issues: {outstanding}")
        else:
            st.success("No outstanding issues.")

        st.markdown("**Decision Summary**")
        st.info(approval_reason(trade))

        if not trade.construction_complete:
            st.warning("Construction is not marked complete yet. The approval engine will remain in WAIT mode.")

        if trade.warnings:
            with st.expander("Approval Warnings", expanded=False):
                for warning in trade.warnings:
                    st.warning(warning)

        if trade.validation_messages:
            with st.expander("Approval Evidence", expanded=False):
                for message in trade.validation_messages:
                    st.write(f"• {message}")

        st.caption("Phase 4 approval engine.")
        responsive_block_end()


# ============================================================
# Step 6 — Execution Package
# ============================================================

def render_execution_package(trade):
    section_header(
        "Step 7",
        "Execution Package",
        "Generated order ticket and management plan.",
    )

    trade = approve_trade(trade)
    ticket = build_execution_ticket(trade)

    strategy = trade.active_strategy() or "Pending"
    symbol = trade.symbol or "Pending"

    with st.container(border=True):
        responsive_block_start("otcc-compact-card")
        st.markdown("### Execution Summary")
        render_native_metric_grid(
            [
                ("Underlying", symbol),
                ("Strategy", strategy),
                ("Expiration", str(getattr(trade, "expiration", "") or "Pending")),
                ("Strike", f"{float(getattr(trade, 'strike', 0.0) or 0.0):.2f}" if float(getattr(trade, 'strike', 0.0) or 0.0) > 0 else "Pending"),
                ("Premium", money(getattr(trade, "premium", 0.0) or 0.0)),
                ("Contracts", int(getattr(trade, "contracts", 0) or 0)),
                ("Buying Power", money(getattr(trade, "buying_power_required", 0.0) or 0.0)),
                ("Maximum Risk", money(getattr(trade, "max_loss", 0.0) or 0.0)),
                ("Maximum Profit", money(getattr(trade, "max_profit", 0.0) or 0.0)),
                ("Reward / Risk", f"{float(getattr(trade, 'reward_risk_ratio', 0.0) or 0.0):,.4f}"),
                ("Breakeven", money(getattr(trade, "breakeven", 0.0) or 0.0)),
            ],
            columns=4,
            block_class="otcc-grid-4",
        )

        with st.expander("OMS Ticket", expanded=False):
            st.code(ticket["order_summary"], language="text")

        with st.expander("Entry Plan", expanded=False):
            trade.entry_plan = st.text_area(
                "Entry Plan",
                value=ticket["entry_plan"],
                key="otcc_entry_plan",
            )

        with st.expander("Exit Plan", expanded=False):
            trade.exit_plan = st.text_area(
                "Exit Plan",
                value=ticket["exit_plan"],
                key="otcc_exit_plan",
            )

        with st.expander("Assignment Plan", expanded=False):
            trade.assignment_plan = st.text_area(
                "Assignment Plan",
                value=ticket["assignment_plan"],
                key="otcc_assignment_plan",
            )

        with st.expander("Risk Notes", expanded=False):
            trade.risk_notes = st.text_area(
                "Risk Notes",
                value=ticket["risk_notes"],
                key="otcc_risk_notes",
            )
        responsive_block_end()


# ============================================================
# Main
# ============================================================

def main():
    trade = get_trade()
    inject_commander_css()
    packet = apply_decision_packet_if_needed(trade)

    # On page load, resolve Decision Review immediately from current trade
    # state and persist it to lifecycle without requiring user interaction.
    has_valid_context = bool(
        (packet is not None and (getattr(packet, "symbol", "") or getattr(packet, "recommended_strategy", "")))
        or (str(getattr(trade, "symbol", "") or "").strip() and str(trade.active_strategy() or trade.recommended_strategy or "").strip())
    )
    if has_valid_context:
        packet = sync_execution_review_to_lifecycle(trade, packet, resolve_confidence=True)


    st.title(f"{PAGE_ICON} Options Decision Center")
    st.caption(
        "Institutional workflow for receiving, evaluating, validating, and approving options trades."
    )

    with st.expander("ℹ️ How to use Options Decision Center", expanded=False):
        st.markdown(
            "Workflow: Mission Briefing -> Strategy Recommendation -> Institutional Review -> Trade Construction -> "
            "Risk Validation -> Trade Approval -> Execution Package"
        )

    render_step_separator()
    if packet is not None:
        render_opportunity_briefing(trade, packet)
    else:
        render_opportunity_selection(trade)

    render_workflow_progress(trade, packet)

    render_step_separator()
    responsive_block_start("otcc-step23-row")
    col_left, col_right = st.columns([0.95, 1.15], gap="medium")
    with col_left:
        render_strategy_selection(trade, packet)
    with col_right:
        packet = render_commander_approval(trade, packet)
    responsive_block_end()

    render_step_separator()
    render_trade_construction(trade, packet)

    render_step_separator()
    render_risk_validation(trade)

    render_step_separator()
    responsive_block_start("otcc-step67-row")
    col_approval, col_execution = st.columns(2, gap="medium")
    with col_approval:
        render_trade_approval(trade, packet)
    with col_execution:
        render_execution_package(trade)
    responsive_block_end()


def run_page():
    main()


if __name__ == "__main__":
    main()
