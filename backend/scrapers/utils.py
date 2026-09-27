"""Small helpers shared across the source scrapers."""
import re
from typing import Optional


def parse_price(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    s = text.replace("\xa0", " ").strip()
    m = re.search(r"\d[\d.,]*", s)
    if not m:
        return None
    num = m.group(0)
    if "." in num and "," in num:
        num = num.replace(".", "").replace(",", ".")
    elif "," in num:
        num = num.replace(",", ".")
    try:
        return float(num)
    except ValueError:
        return None


PLATFORM_TABLE = [
    ("playstation 5", "PS5"), ("ps5", "PS5"),
    ("playstation 4", "PS4"), ("ps4", "PS4"),
    ("playstation 3", "PS3"), ("ps3", "PS3"),
    ("playstation vita", "PS Vita"), ("ps vita", "PS Vita"), ("psp", "PSP"),
    ("nintendo switch 2", "Switch 2"), ("switch 2", "Switch 2"),
    ("nintendo switch", "Switch"), ("switch", "Switch"),
    ("xbox series", "Xbox Series"), ("xbox one", "Xbox One"),
    ("xbox 360", "Xbox 360"), ("xbox", "Xbox"),
    ("nintendo 3ds", "3DS"), ("3ds", "3DS"),
    ("nintendo wii u", "Wii U"), ("wii u", "Wii U"), ("wii", "Wii"),
    ("gamecube", "GameCube"), ("dreamcast", "Dreamcast"),
    ("pc", "PC"), ("steam", "PC"),
]


def short_platform(text: str) -> str:
    """Normalize a platform label to a short badge (e.g. 'Nintendo Switch' -> 'Switch')."""
    if not text:
        return text
    t = text.strip()
    low = t.lower()
    for needle, label in PLATFORM_TABLE:
        if needle in low:
            return label
    return t[:12]
