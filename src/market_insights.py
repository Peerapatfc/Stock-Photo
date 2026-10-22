"""Market signals measured from Adobe Stock search (see docs/market_research_th.md).

data/market_insights.json is refreshed weekly by the `adobe-stock-market-research` scheduled task.
Everything here degrades to "no adjustment" when the file is missing, stale or has too little data.
"""
import json
import logging
from datetime import date, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

MAX_AGE_DAYS = 60
MIN_HUMAN_RESULTS = 500   # ignore terms with too few results to mean anything
MULT_MIN, MULT_MAX = 0.6, 1.5


def load(path: Path) -> dict:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def term_opportunity(m: dict) -> float | None:
    """sell_through * (1 - ai_share). sell_through = share of non-AI photos Adobe no longer calls 'undiscovered'."""
    human, ai, undisc = m.get("human", 0), m.get("ai", 0), m.get("human_undisc", 0)
    if human < MIN_HUMAN_RESULTS:
        return None
    sell_through = 1 - undisc / human
    ai_share = ai / (ai + human)
    return sell_through * (1 - ai_share)


def niche_scores(insights: dict) -> dict[str, float]:
    scores = {}
    for niche, terms in insights.get("terms", {}).items():
        vals = [v for v in (term_opportunity(m) for m in terms.values()) if v is not None]
        if vals:
            scores[niche] = sum(vals) / len(vals)
    return scores


def niche_multipliers(insights: dict, today: date | None = None) -> dict[str, float]:
    """Weight multiplier per niche in [0.6, 1.5]; empty (=> 1.0 everywhere) when data is missing or stale."""
    today = today or date.today()
    try:
        updated = date.fromisoformat(insights.get("updated", ""))
    except ValueError:
        return {}
    if today - updated > timedelta(days=MAX_AGE_DAYS):
        log.warning(f"market_insights is {(today - updated).days} days old — ignoring")
        return {}
    scores = niche_scores(insights)
    if len(scores) < 2:
        return {}
    mean = sum(scores.values()) / len(scores)
    return {n: max(MULT_MIN, min(MULT_MAX, s / mean)) for n, s in scores.items()}


def keyword_hints(insights: dict, niche: str, limit: int = 15) -> list[str]:
    """Words frequent in titles of top-ranked listings for this niche's search terms (filled by the weekly task)."""
    return list(insights.get("keyword_hints", {}).get(niche, []))[:limit]
