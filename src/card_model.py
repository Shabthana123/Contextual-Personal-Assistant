from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Card:
    description: str
    card_type: str                 # Task / Reminder / Idea
    date_text: Optional[str]       # raw date text like "next Monday"
    date_parsed: Optional[str]     # ISO datetime string or None
    assignee: Optional[str]
    context_keywords: List[str]
    envelope_id: Optional[int] = None

@dataclass
class Envelope:
    name: str
    description: Optional[str] = None
