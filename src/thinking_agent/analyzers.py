# src/thinking_agent/analyzers.py
from typing import List, Dict, Any, Optional
from collections import defaultdict
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
import math

def _parse_iso(date_iso: Optional[str]):
    if not date_iso:
        return None
    try:
        return datetime.fromisoformat(date_iso)
    except Exception:
        # fallback: try trimming timezone Z if present
        try:
            if date_iso.endswith("Z"):
                return datetime.fromisoformat(date_iso[:-1])
        except Exception:
            return None

def detect_conflicts(cards: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Detect duplicates and simple conflicts:
      - duplicate descriptions (case-insensitive)
      - same assignee & same-day tasks (date_parsed)
    Returns dict with 'duplicates' and 'assignee_date_conflicts' lists.
    """
    duplicates = []
    desc_map = defaultdict(list)
    for c in cards:
        desc_map[c.get("description", "").strip().lower()].append(c)
    for desc, group in desc_map.items():
        if len(group) > 1:
            duplicates.append({
                "description": desc,
                "cards": [{"id": g.get("id"), "envelope_id": g.get("envelope_id"), "description": g.get("description")} for g in group]
            })

    assignee_conflicts = []
    by_assignee = defaultdict(list)
    for c in cards:
        a = c.get("assignee")
        if a:
            by_assignee[a].append(c)

    for assignee, items in by_assignee.items():
        date_groups = defaultdict(list)
        for c in items:
            d = _parse_iso(c.get("date_parsed"))
            if d:
                date_groups[d.date()].append(c)
        for dday, cs in date_groups.items():
            if len(cs) > 1:
                assignee_conflicts.append({
                    "assignee": assignee,
                    "date": dday.isoformat(),
                    "cards": [{"id": c.get("id"), "description": c.get("description")} for c in cs]
                })

    return {"duplicates": duplicates, "assignee_date_conflicts": assignee_conflicts}

def cluster_ideas(cards: List[Dict[str, Any]], embeddings: np.ndarray,
                  min_cluster_size: int = 2, n_clusters: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Cluster card descriptions using KMeans on provided embeddings.
    Returns clusters with size >= min_cluster_size.
    `embeddings` must align with `cards` order.
    """
    if len(cards) == 0:
        return []
    if embeddings is None or len(embeddings) == 0:
        return []

    num_cards = len(cards)
    if num_cards < 2:
        return []

    # Heuristic for number of clusters
    if n_clusters is None:
        n_clusters = max(2, int(math.sqrt(num_cards)))
    n_clusters = min(n_clusters, num_cards)

    # Fit KMeans (deterministic random_state)
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(embeddings)

    clusters = defaultdict(list)
    for idx, lbl in enumerate(labels):
        clusters[int(lbl)].append(idx)

    results = []
    for lbl, idxs in clusters.items():
        if len(idxs) >= min_cluster_size:
            # compute centroid and representative
            centroid = km.cluster_centers_[lbl]
            sims = cosine_similarity([centroid], embeddings[idxs])[0]
            rep_local_idx = int(np.argmax(sims))
            rep_idx = idxs[rep_local_idx]
            rep_card = cards[rep_idx]
            members = [{"id": cards[i].get("id"), "description": cards[i].get("description"), "envelope_id": cards[i].get("envelope_id")} for i in idxs]
            results.append({
                "cluster_id": int(lbl),
                "size": len(idxs),
                "representative": {"id": rep_card.get("id"), "description": rep_card.get("description")},
                "members": members
            })
    return results

def suggest_next_steps(cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Simple heuristics to produce suggestions:
    - If multiple tasks in an envelope lack dates -> recommend scheduling
    - If a task mentions 'follow up' / 'finish' but has no date -> suggest add date
    """
    suggestions = []
    tasks = [c for c in cards if c.get("card_type", "").lower() == "task"]
    env_map = defaultdict(list)
    for t in tasks:
        env_map[t.get("envelope_id")].append(t)

    for eid, ts in env_map.items():
        lacking_dates = [t for t in ts if not t.get("date_parsed")]
        if len(lacking_dates) >= 2:
            suggestions.append({
                "type": "schedule_recommendation",
                "envelope_id": eid,
                "reason": f"{len(lacking_dates)} tasks in envelope have no dates; consider scheduling or prioritizing",
                "sample_tasks": [{"id": t.get("id"), "description": t.get("description")} for t in lacking_dates[:5]]
            })

    action_words = ["finish", "start", "follow up", "follow-up", "handover", "assign"]
    for t in tasks:
        desc = (t.get("description") or "").lower()
        for a in action_words:
            if a in desc and not t.get("date_parsed"):
                suggestions.append({
                    "type": "add_date",
                    "card_id": t.get("id"),
                    "reason": f"Task mentions '{a}' but has no date. Consider scheduling."
                })
                break

    return suggestions
