# src/db_manager.py
import sqlite3
from pathlib import Path
import json
from typing import List, Optional
from src.card_model import Card, Envelope

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "assistant.db"

class DBManager:
    def __init__(self, db_path: Optional[str] = None):
        db_file = db_path if db_path else str(DB_PATH)
        Path(db_file).resolve().parents[0].mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        c = self.conn.cursor()
        # Envelopes
        c.execute("""
        CREATE TABLE IF NOT EXISTS Envelopes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        # Cards (organization omitted). date_parsed is stored as text (ISO) when present
        c.execute("""
        CREATE TABLE IF NOT EXISTS Cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_type TEXT,
            description TEXT,
            date_text TEXT,
            date_parsed TEXT,
            assignee TEXT,
            context_keywords TEXT,
            envelope_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(envelope_id) REFERENCES Envelopes(id)
        )""")
        # UserContext
        c.execute("""
        CREATE TABLE IF NOT EXISTS UserContext (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        self.conn.commit()

    # Envelopes CRUD
    def add_envelope(self, envelope: Envelope) -> int:
        c = self.conn.cursor()
        c.execute("INSERT INTO Envelopes (name, description) VALUES (?, ?)",
                  (envelope.name, envelope.description))
        self.conn.commit()
        return c.lastrowid

    def get_all_envelopes(self) -> List[dict]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM Envelopes ORDER BY created_at DESC")
        return [dict(r) for r in c.fetchall()]

    def get_envelope_by_id(self, eid: int) -> Optional[dict]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM Envelopes WHERE id = ?", (eid,))
        row = c.fetchone()
        return dict(row) if row else None

    # Cards CRUD
    def add_card(self, card: Card) -> int:
        c = self.conn.cursor()
        c.execute("""
        INSERT INTO Cards (card_type, description, date_text, date_parsed, assignee, context_keywords, envelope_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            card.card_type,
            card.description,
            card.date_text,
            card.date_parsed,
            card.assignee,
            json.dumps(card.context_keywords),
            card.envelope_id
        ))
        self.conn.commit()
        return c.lastrowid

    def get_all_cards(self) -> List[dict]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM Cards ORDER BY created_at DESC")
        rows = c.fetchall()
        cards = []
        for r in rows:
            d = dict(r)
            d['context_keywords'] = json.loads(d['context_keywords']) if d['context_keywords'] else []
            cards.append(d)
        return cards

    def get_cards_by_envelope(self, envelope_id: int) -> List[dict]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM Cards WHERE envelope_id = ? ORDER BY created_at DESC", (envelope_id,))
        rows = c.fetchall()
        res = []
        for r in rows:
            d = dict(r)
            d['context_keywords'] = json.loads(d['context_keywords']) if d['context_keywords'] else []
            res.append(d)
        return res

    # UserContext CRUD
    def update_context(self, key: str, value: str):
        c = self.conn.cursor()
        c.execute("""
        INSERT INTO UserContext (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
        """, (key, value))
        self.conn.commit()

    def get_context(self, key: str) -> Optional[str]:
        c = self.conn.cursor()
        c.execute("SELECT value FROM UserContext WHERE key = ?", (key,))
        row = c.fetchone()
        return row['value'] if row else None
