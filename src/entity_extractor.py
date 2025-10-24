# src/entity_extractor.py

import spacy
from dateparser.search import search_dates
from typing import Dict, Any, List
import datetime
import re

nlp = spacy.load("en_core_web_md")

# Words to ignore for keywords
STOPWORDS = {
    "call", "email", "meet", "send", "remind", "remember",
    "prepare", "submit", "finish", "schedule", "follow", "up",
    "dont", "don't", "be", "a", "the", "should", "is", "on", "at", "for", "to"
}

# Updated regex to capture dynamic teams like "Team 1", "Team A", "purple team", or "Marketing Team"
TEAM_REGEX = re.compile(
    r'\b(?:'
    r'marketing|sales|hr|engineering|'           # predefined teams
    r'[A-Za-z0-9]+ team|'                        # dynamic prefix e.g., "Marketing Team", "Purple Team"
    r'team [A-Za-z0-9]+'                         # dynamic suffix e.g., "Team 1", "Team A"
    r')\b',
    re.I
)



class EntityExtractor:
    def __init__(self):
        self.nlp = nlp

    def clean_text(self, text: str) -> str:
        doc = self.nlp(text)
        tokens = [t.text for t in doc if t.text.lower() not in STOPWORDS]
        return " ".join(tokens)

    def extract(self, text: str) -> Dict[str, Any]:
        clean_note = self.clean_text(text)
        doc = self.nlp(text)  # original text for NER
        doc_keywords = self.nlp(clean_note)

        # Assignee detection
        assignee = None

        # Check for PERSON entities
        persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
        if persons:
            assignee = persons[0]

        # # Check for teams/orgs
        # if not assignee:
        #     team_match = TEAM_REGEX.search(text)
        #     if team_match:
        #         assignee = team_match.group(0).title()

        # TEAM/ORG detection
        if not assignee:
            team_matches = TEAM_REGEX.findall(text)
            if team_matches:
                # Pick the longest match (e.g., "Marketing Team" > "Team")
                assignee = max(team_matches, key=len).title()

        # Check pronouns fallback
        if not assignee:
            pronouns = {"me", "i", "myself", "mine", "my"}
            tokens = [t.text.lower() for t in doc]
            for p in pronouns:
                if p in tokens:
                    assignee = "Me"
                    break

        # DATE extraction
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

        # Context keywords
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
