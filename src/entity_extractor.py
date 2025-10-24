# src/entity_extractor.py

import spacy
from dateparser.search import search_dates
from typing import Dict, Any, List
import datetime

nlp = spacy.load("en_core_web_md")

# Words to ignore for assignee & keyword extraction
STOPWORDS = {
    "call", "email", "meet", "send", "remind", "remember",
    "prepare", "submit", "finish", "schedule", "follow", "up",
    "dont", "don't", "be", "a", "the", "should", "is", "on", "at", "for", "to"
}

class EntityExtractor:
    def __init__(self):
        self.nlp = nlp

    def clean_text(self, text: str) -> str:
        doc = self.nlp(text)
        tokens = [t.text for t in doc if t.text.lower() not in STOPWORDS]
        return " ".join(tokens)

    def extract(self, text: str) -> Dict[str, Any]:
        clean_note = self.clean_text(text)
        doc = self.nlp(text)  # original text for PERSON & DATE
        doc_keywords = self.nlp(clean_note)

        # ----------------------------
        # Extract PERSON entities as assignee
        # ----------------------------
        persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
        assignee = None
        if persons:
            first_person = persons[0].split()
            if first_person[0].lower() in STOPWORDS:
                assignee = " ".join(first_person[1:])
            else:
                assignee = persons[0]
        else:
            # fallback for pronouns
            pronouns = {"me", "i", "myself", "mine", "my"}
            tokens = [t.text.lower() for t in doc]
            for p in pronouns:
                if p in tokens:
                    assignee = "Me"
                    break

        # ----------------------------
        # DATE extraction
        # ----------------------------
        date_text = None
        date_parsed = None
        results = search_dates(
            text,
            settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": datetime.datetime.now(),
                "RETURN_AS_TIMEZONE_AWARE": False
            }
        )

        if results:
            for candidate_text, dt in results:
                if len(candidate_text.strip()) > 2 or any(c.isdigit() for c in candidate_text):
                    date_text = candidate_text.strip()
                    date_parsed = dt.isoformat()
                    break

        # 🔹 Retry if not parsed — handles “on next Sunday” etc.
        if not date_parsed:
            cleaned_text = text.replace(" on ", " ").replace(" at ", " ")
            results = search_dates(
                cleaned_text,
                settings={
                    "PREFER_DATES_FROM": "future",
                    "RELATIVE_BASE": datetime.datetime.now(),
                    "RETURN_AS_TIMEZONE_AWARE": False
                }
            )
            if results:
                for candidate_text, dt in results:
                    if len(candidate_text.strip()) > 2 or any(c.isdigit() for c in candidate_text):
                        date_text = candidate_text.strip()
                        date_parsed = dt.isoformat()
                        break

        # ----------------------------
        # Context keywords
        # ----------------------------
        keywords: List[str] = []
        for token in doc_keywords:
            if token.pos_ in ("NOUN", "PROPN") and token.text.lower() not in STOPWORDS:
                k = token.text.strip().lower()
                if k and k not in keywords:
                    keywords.append(k)
        if not keywords:
            keywords = [w.lower() for w in clean_note.split()[:6] if w.lower() not in STOPWORDS]

        return {
            "assignee": assignee,
            "date_text": date_text,
            "date_parsed": date_parsed,
            "context_keywords": keywords,
            "raw_entities": [(ent.text, ent.label_) for ent in doc.ents],
        }
