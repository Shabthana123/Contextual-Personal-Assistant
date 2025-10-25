# src/thinking_agent/persistence.py
import json
import sqlite3
from typing import Any, Dict, List, Optional

class Persistence:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self._ensure_table()

    def _ensure_table(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT,
                payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def persist(self, kind: str, payload: Dict[str, Any]) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO Recommendations (kind, payload) VALUES (?, ?)",
            (kind, json.dumps(payload))
        )
        self.conn.commit()
        return cur.lastrowid

    def list_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, kind, payload, created_at FROM Recommendations ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        out = []
        for r in rows:
            try:
                payload = json.loads(r["payload"])
            except Exception:
                payload = {"raw": r["payload"]}
            out.append({
                "id": r["id"],
                "kind": r["kind"],
                "payload": payload,
                "created_at": r["created_at"]
            })
        return out
