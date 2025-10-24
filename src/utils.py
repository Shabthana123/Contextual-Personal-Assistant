# src/utils.py

import spacy
from difflib import SequenceMatcher

# Load medium model for semantic similarity
nlp = spacy.load("en_core_web_md")

IGNORE_WORDS = {
    "call", "email", "meet", "send", "remind", "remember",
    "prepare", "submit", "finish", "schedule", "follow", "up",
    "dont", "don't", "idea", "note", "the", "a", "on", "at", "in",
    "to", "for", "with", "way", "me", "my", "i"
}

TOPIC_KEYWORDS = [
    "budget", "project", "plan", "meeting", "report", "school",
    "family", "fruit", "fruits", "vegetable", "grocery", "milk",
    "bread", "logo", "design", "brand", "sales", "research", "ai"
]

MODIFIER_KEYWORDS = [
    "Q1", "Q2", "Q3", "Q4", "2025", "2026", "January", "February",
    "March", "April", "May", "June", "July", "August", "September",
    "October", "November", "December"
]


def generate_envelope_name_from_text(text: str, context=None) -> str:
    """
    Generate an envelope name for a given text using semantic and contextual cues.
    Prevents duplicates by checking similarity with existing envelopes.
    """
    doc = nlp(text.lower())

    # --- Step 1: Check similarity with existing envelopes ---
    if context and "envelopes" in context:
        best_match, best_score = None, 0
        for envelope_name in context["envelopes"]:
            sim_score = nlp(text).similarity(nlp(envelope_name))
            seq_score = SequenceMatcher(None, text.lower(), envelope_name.lower()).ratio()
            combined_score = (sim_score + seq_score) / 2
            if combined_score > best_score:
                best_match, best_score = envelope_name, combined_score

        # If similar enough, reuse existing envelope
        if best_score >= 0.75:
            return best_match.title()

    # --- Step 2: Entity-based detection ---
    for ent in doc.ents:
        if ent.label_ in ("ORG", "WORK_OF_ART", "EVENT") and any(
            k in ent.text.lower() for k in TOPIC_KEYWORDS
        ):
            return ent.text.strip().title()

    # --- Step 3: Topic + modifier detection ---
    topic = None
    modifier = None
    for token in doc:
        if token.text.lower() in TOPIC_KEYWORDS:
            topic = token.text.capitalize()
        if token.text in MODIFIER_KEYWORDS:
            modifier = token.text
    if topic:
        return f"{modifier + ' ' if modifier else ''}{topic}"

    # --- Step 4: Category mapping ---
    category_mappings = {
        ("fruit", "fruits", "vegetable", "grocery", "milk", "bread"): "Groceries",
        ("child", "kids", "family", "school", "father", "mother"): "Family",
        ("logo", "design", "brand", "color", "poster"): "Brand Design",
        ("sales", "forecast", "report"): "Sales",
        ("research", "ai", "study", "paper"): "AI Research",
    }

    for keywords, category in category_mappings.items():
        for word in keywords:
            if word in text.lower():
                return category

    # --- Step 5: Fallback — use short noun chunks ---
    meaningful_chunks = [
        chunk.text.strip().title()
        for chunk in doc.noun_chunks
        if len(chunk.text.split()) <= 3
    ]
    if meaningful_chunks:
        return meaningful_chunks[0]

    # --- Step 6: Fallback — verbs ---
    verbs = [
        token.lemma_.capitalize()
        for token in doc
        if token.pos_ == "VERB" and token.text.lower() not in IGNORE_WORDS
    ]
    if verbs:
        return verbs[0]

    return "General"
