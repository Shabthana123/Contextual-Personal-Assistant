# src/ingestion_agent.py
from src.entity_extractor import EntityExtractor
from src.card_model import Card, Envelope
from src.db_manager import DBManager
from src.context_manager import ContextManager
from src.utils import generate_envelope_name_from_text
from typing import Optional, List
import spacy

nlp = spacy.load("en_core_web_md")  # medium model for better similarity

class IngestionAgent:
    def __init__(self, db: Optional[DBManager] = None):
        self.db = db if db else DBManager()
        self.extractor = EntityExtractor()
        self.context_manager = ContextManager(self.db)

    def normalize_text(self, text: str) -> str:
        """Lowercase and strip for comparison."""
        return (text or "").strip().lower()

    def classify_card_type(self, text: str) -> str:
        t = text.lower()
        task_keywords = {"call", "email", "meet", "schedule", "send", "submit",
                         "prepare", "finish", "follow up", "follow-up", "assign", "pick up", "pick-up"}
        reminder_keywords = {"remind", "remember", "reminder", "don't forget", "dont forget","not forget"}

        if any(k in t for k in reminder_keywords):
            return "Reminder"
        if any(k in t for k in task_keywords):
            return "Task"
        return "Idea"

    def assign_envelope(self, keywords: List[str], note_text: str) -> int:
        """
        Assign card to most relevant existing envelope:
        1) Exact keyword match
        2) Semantic similarity with existing envelopes
        3) Create a new envelope if no match
        """
        envelopes = self.db.get_all_envelopes()
        note_doc = nlp(note_text.lower())
        context = self.context_manager.get_refined_context()

        # --- 1. Check exact keyword match first ---
        for env in envelopes:
            env_name_norm = self.normalize_text(env.get("name", ""))
            if any(k.lower() in env_name_norm for k in keywords):
                return env["id"]

        # --- 2. Context-guided thematic name ---
        thematic_envelope = generate_envelope_name_from_text(note_text, context)
        for env in envelopes:
            if self.normalize_text(env.get("name")) == self.normalize_text(thematic_envelope):
                return env["id"]

        # --- 3. Semantic similarity check ---
        best_score = 0
        best_env_id = None
        for env in envelopes:
            env_text = (env.get("name") or "") + " " + (env.get("description") or "")
            env_doc = nlp(env_text.lower())
            sim_score = note_doc.similarity(env_doc)

            # Context-based boosting
            project_score = context["projects"].get(env.get("name", ""), 0)
            theme_score = sum(context["themes"].get(k, 0) for k in keywords)
            total_score = sim_score + 0.1 * project_score + 0.05 * theme_score

            overlap = any(k.lower() in env_text.lower() for k in keywords)
            if total_score > best_score and (sim_score > 0.6 or overlap):
                best_score = total_score
                best_env_id = env["id"]

        if best_score >= 0.6 and best_env_id:
            return best_env_id

        # --- 4. Create new envelope if nothing matched ---
        name = generate_envelope_name_from_text(note_text, context)
        env = Envelope(name=name)
        return self.db.add_envelope(env)

    def process_note(self, note: str) -> dict:
        note_text = note.strip()
        entities = self.extractor.extract(note_text)
        card_type = self.classify_card_type(note_text)

        # Commit DB before envelope assignment
        self.db.conn.commit()

        envelope_id = self.assign_envelope(entities["context_keywords"], note_text)

        # --- Check for duplicate in the same envelope ---
        existing_cards = self.db.get_cards_by_envelope(envelope_id)
        for existing in existing_cards:
            if self.normalize_text(existing["description"]) == self.normalize_text(note_text):
                # Exact duplicate found, return existing
                return existing

        # --- Create and store new card ---
        card = Card(
            description=note_text,
            card_type=card_type,
            date_text=entities["date_text"],
            date_parsed=entities["date_parsed"],
            assignee=entities["assignee"],
            context_keywords=entities["context_keywords"],
            envelope_id=envelope_id
        )
        card_id = self.db.add_card(card)

        # --- Update user context ---
        self.context_manager.update_context_from_card(card)

        return {
            "id": card_id,
            "description": card.description,
            "card_type": card.card_type,
            "date_text": card.date_text,
            "date_parsed": card.date_parsed,
            "assignee": card.assignee,
            "context_keywords": card.context_keywords,
            "envelope_id": card.envelope_id
        }
