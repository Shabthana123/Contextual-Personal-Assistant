# src/thinking_agent/agent.py
from src.db_manager import DBManager
from src.thinking_agent.embeddings import embed_texts
from src.thinking_agent.analyzers import detect_conflicts, cluster_ideas, suggest_next_steps
from typing import List, Dict, Any, Optional
import json
import numpy as np

class ThinkingAgent:
    """
    Top-level orchestrator:
    - fetch cards
    - compute embeddings
    - run analyzers
    - persist recommendations in DB table ThinkingRecommendations
    """
    def __init__(self, db: Optional[DBManager] = None):
        self.db = db if db else DBManager()
        self._ensure_table()

    def _ensure_table(self):
        c = self.db.conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS ThinkingRecommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            kind TEXT,
            payload TEXT
        )
        """)
        self.db.conn.commit()

    def _persist(self, kind: str, payload: Dict[str, Any]):
        c = self.db.conn.cursor()
        c.execute("INSERT INTO ThinkingRecommendations (kind, payload) VALUES (?, ?)",
                  (kind, json.dumps(payload)))
        self.db.conn.commit()

    def fetch_cards(self) -> List[Dict[str, Any]]:
        """
        Use DBManager.get_all_cards to fetch cards.
        It returns descriptions and context_keywords already parsed into lists.
        """
        return self.db.get_all_cards()

    def fetch_envelopes(self) -> List[Dict[str, Any]]:
        return self.db.get_all_envelopes()

    def run_once(self) -> Dict[str, Any]:
        cards = self.fetch_cards()
        envelopes = self.fetch_envelopes()
        summary = {"num_cards": len(cards), "num_envelopes": len(envelopes)}

        # Preprocess card structure for analyzers
        # Ensure fields used by analyzers: id, description, envelope_id, assignee, date_parsed, card_type
        proc_cards = []
        for c in cards:
            proc_cards.append({
                "id": c.get("id"),
                "description": c.get("description"),
                "envelope_id": c.get("envelope_id"),
                "assignee": c.get("assignee"),
                "date_parsed": c.get("date_parsed"),
                "card_type": c.get("card_type")
            })

        # 1) conflict detection
        conflicts = detect_conflicts(proc_cards)
        for dup in conflicts.get("duplicates", []):
            self._persist("duplicate", dup)
        for ac in conflicts.get("assignee_date_conflicts", []):
            self._persist("assignee_conflict", ac)

        # 2) embeddings + clustering
        texts = [c["description"] or "" for c in proc_cards]
        clusters = []
        if texts:
            embs = embed_texts(texts)
            clusters = cluster_ideas(proc_cards, embeddings=embs)
            for cl in clusters:
                self._persist("cluster_suggestion", cl)

        # 3) next steps suggestions
        suggestions = suggest_next_steps(proc_cards)
        for s in suggestions:
            self._persist("suggestion", s)

        # Build final return dict
        result = {
            "summary": summary,
            "duplicates": conflicts.get("duplicates", []),
            "conflicts": conflicts.get("assignee_date_conflicts", []),
            "idea_clusters": clusters,
            "next_steps": suggestions
        }
        return result

    def get_recent_recommendations(self, limit: int = 50) -> List[Dict[str, Any]]:
        c = self.db.conn.cursor()
        c.execute("SELECT id, created_at, kind, payload FROM ThinkingRecommendations ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        res = []
        for r in rows:
            res.append({
                "id": r["id"],
                "created_at": r["created_at"],
                "kind": r["kind"],
                "payload": json.loads(r["payload"])
            })
        return res

    def clear_recommendations(self):
        c = self.db.conn.cursor()
        c.execute("DELETE FROM ThinkingRecommendations")
        self.db.conn.commit()
