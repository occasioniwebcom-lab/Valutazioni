"""Generate a small set of useful marketplace queries without user intervention."""
import re


def variants(query: str):
    clean = re.sub(r"\s+", " ", query.strip())
    if not clean:
        return []
    values = [clean]
    for suffix in (" videogioco", " gioco", " ps5", " ps4", " ps3", " xbox", " switch"):
        if suffix.strip() not in clean.lower():
            values.append(f"{clean}{suffix}")
    return values