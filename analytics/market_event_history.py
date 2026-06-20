# =========================================================
# 🧠 MARKET EVENT HISTORY — v45
# JFBP Quant Desk
# Local SQLite Market Memory
# Historical Regime Persistence
# =========================================================

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd


# =========================================================
# DATABASE PATH
# =========================================================

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "market_events.db"


# =========================================================
# DATABASE INIT / MIGRATION
# =========================================================

def init_market_event_db() -> None:
    """
    Creates the market event database if it does not exist and safely
    upgrades older databases with the v45 regime/breadth columns.
    """

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS market_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_date TEXT NOT NULL,
                event_label TEXT NOT NULL,
                confidence INTEGER,
                stress_score INTEGER,
                stress_label TEXT,
                scanner_regime TEXT,
                breadth_state TEXT,
                breadth_score REAL,
                execution_multiplier REAL,
                qqq REAL,
                spy REAL,
                dia REAL,
                iwm REAL,
                vixy REAL,
                portfolio_move REAL,
                created_at TEXT NOT NULL
            )
            """
        )

        existing_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(market_events)"
            ).fetchall()
        }

        migrations = {
            "scanner_regime": "TEXT",
            "breadth_state": "TEXT",
            "breadth_score": "REAL",
            "execution_multiplier": "REAL",
        }

        for column_name, column_type in migrations.items():
            if column_name not in existing_columns:
                conn.execute(
                    f"ALTER TABLE market_events ADD COLUMN {column_name} {column_type}"
                )

        conn.commit()


# =========================================================
# SAVE EVENT
# =========================================================

def save_market_event(
    event_label: str,
    confidence: int,
    stress_score: int,
    stress_label: str,
    qqq: Optional[float],
    spy: Optional[float],
    dia: Optional[float],
    iwm: Optional[float],
    vixy: Optional[float],
    portfolio_move: Optional[float],
    scanner_regime: Optional[str] = None,
    breadth_state: Optional[str] = None,
    breadth_score: Optional[float] = None,
    execution_multiplier: Optional[float] = None,
) -> None:
    """
    Saves one market event per date/event_label combination.

    If the same event is saved again on the same day,
    the row is updated instead of duplicated.

    v45 persists the actual scanner regime, breadth state,
    breadth score, and execution multiplier at the time of save.
    """

    init_market_event_db()

    event_date = datetime.now().strftime("%Y-%m-%d")
    created_at = datetime.now().isoformat(timespec="seconds")

    with sqlite3.connect(DB_PATH) as conn:
        existing = conn.execute(
            """
            SELECT id
            FROM market_events
            WHERE event_date = ?
              AND event_label = ?
            """,
            (
                event_date,
                event_label,
            ),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE market_events
                SET
                    confidence = ?,
                    stress_score = ?,
                    stress_label = ?,
                    scanner_regime = ?,
                    breadth_state = ?,
                    breadth_score = ?,
                    execution_multiplier = ?,
                    qqq = ?,
                    spy = ?,
                    dia = ?,
                    iwm = ?,
                    vixy = ?,
                    portfolio_move = ?,
                    created_at = ?
                WHERE id = ?
                """,
                (
                    confidence,
                    stress_score,
                    stress_label,
                    scanner_regime,
                    breadth_state,
                    breadth_score,
                    execution_multiplier,
                    qqq,
                    spy,
                    dia,
                    iwm,
                    vixy,
                    portfolio_move,
                    created_at,
                    existing[0],
                ),
            )

        else:
            conn.execute(
                """
                INSERT INTO market_events (
                    event_date,
                    event_label,
                    confidence,
                    stress_score,
                    stress_label,
                    scanner_regime,
                    breadth_state,
                    breadth_score,
                    execution_multiplier,
                    qqq,
                    spy,
                    dia,
                    iwm,
                    vixy,
                    portfolio_move,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_date,
                    event_label,
                    confidence,
                    stress_score,
                    stress_label,
                    scanner_regime,
                    breadth_state,
                    breadth_score,
                    execution_multiplier,
                    qqq,
                    spy,
                    dia,
                    iwm,
                    vixy,
                    portfolio_move,
                    created_at,
                ),
            )

        conn.commit()


# =========================================================
# LOAD RECENT EVENTS
# =========================================================

def load_recent_market_events(limit: int = 20) -> pd.DataFrame:
    init_market_event_db()

    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT
                event_date AS Date,
                event_label AS Event,
                confidence AS Confidence,
                stress_score AS "Stress Score",
                stress_label AS "Stress Label",
                scanner_regime AS Regime,
                breadth_state AS "Breadth State",
                breadth_score AS "Breadth Score",
                execution_multiplier AS "Position Size",
                qqq AS QQQ,
                spy AS SPY,
                dia AS DIA,
                iwm AS IWM,
                vixy AS VIXY,
                portfolio_move AS "Portfolio Move",
                created_at AS "Saved At"
            FROM market_events
            ORDER BY event_date DESC, created_at DESC
            LIMIT ?
            """,
            conn,
            params=(limit,),
        )

    return df


# =========================================================
# CLEAR HISTORY — MANUAL SAFETY TOOL
# =========================================================

def clear_market_event_history() -> None:
    init_market_event_db()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM market_events")
        conn.commit()
