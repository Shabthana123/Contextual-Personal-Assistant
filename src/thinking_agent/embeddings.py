# src/thinking_agent/embeddings.py
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Optional

_MODEL: Optional[SentenceTransformer] = None

def get_model(name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer(name)
    return _MODEL

def embed_texts(texts: List[str]) -> np.ndarray:
    """
    Compute normalized embeddings for a list of texts using a SentenceTransformer.
    Returns an (N, D) numpy array. If texts empty -> empty array with shape (0, dim).
    """
    if not texts:
        return np.zeros((0, 384))
    model = get_model()
    embs = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return embs
