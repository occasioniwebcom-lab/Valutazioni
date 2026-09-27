"""Fuzzy title matching to line up the same game across GameLife/CeX/eBay results."""
import difflib
import re

_STRIP_WORDS = re.compile(
    r"\b(playstation|ps5|ps4|ps3|ps2|ps1|psvita|ps vita|vita|psp|nintendo|switch|xbox|"
    r"series x|series s|one|360|wii u|wii|3ds|2ds|\bds\b|gamecube|\bpc\b|steam|"
    r"standard|edition|edizione|day one|goty|game of the year|limited|collector'?s?|"
    r"remastered|remake|deluxe|ultimate|complete|italiano|\bita\b|\beu\b|usato|nuovo|new|used)\b",
    re.I,
)
_PUNCT = re.compile(r"[^a-z0-9 ]+")
_SPACES = re.compile(r"\s+")


def normalize_title(title):
    if not title:
        return ""
    t = title.lower()
    t = _PUNCT.sub(" ", t)
    t = _STRIP_WORDS.sub(" ", t)
    t = _SPACES.sub(" ", t).strip()
    return t


def best_match(target_title: str, candidates: list, threshold: float = 0.55):
    """Return the candidate dict (with a 'title' key) most similar to target_title, or None."""
    tnorm = normalize_title(target_title)
    if not tnorm or not candidates:
        return None
    best = None
    best_score = 0.0
    for c in candidates:
        cnorm = normalize_title(c.get("title"))
        if not cnorm:
            continue
        score = difflib.SequenceMatcher(None, tnorm, cnorm).ratio()
        if score > best_score:
            best_score = score
            best = c
    if best is not None and best_score >= threshold:
        return best
    return None


def lowest_price_match(target_title: str, candidates: list, threshold: float = 0.55):
    """Return the cheapest price-bearing candidate among sufficiently similar titles."""
    tnorm = normalize_title(target_title)
    if not tnorm or not candidates:
        return None
    matches = []
    for candidate in candidates:
        cnorm = normalize_title(candidate.get("title"))
        price = candidate.get("price")
        if not cnorm or price is None:
            continue
        score = difflib.SequenceMatcher(None, tnorm, cnorm).ratio()
        if score >= threshold:
            matches.append(candidate)
    return min(matches, key=lambda candidate: candidate["price"], default=None)


def matching_candidates(target_title: str, candidates: list, threshold: float = 0.55):
    """Return all price-bearing candidates with sufficiently similar titles, cheapest first."""
    tnorm = normalize_title(target_title)
    if not tnorm or not candidates:
        return []
    matches = []
    for candidate in candidates:
        cnorm = normalize_title(candidate.get("title"))
        if not cnorm or candidate.get("price") is None:
            continue
        score = difflib.SequenceMatcher(None, tnorm, cnorm).ratio()
        if score >= threshold:
            matches.append(candidate)
    return sorted(matches, key=lambda candidate: candidate["price"])
