"""Le guide d'investissement crypto des agents : un aide-mémoire dans leur prompt, le guide complet à la demande."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

GUIDE_DIR = Path(__file__).parent / "guide"


@lru_cache(maxsize=1)
def full_guide() -> str:
    path = GUIDE_DIR / "guide_crypto.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


@lru_cache(maxsize=1)
def cheat_sheet() -> str:
    path = GUIDE_DIR / "aide_memoire.md"
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def sections() -> dict[int, tuple[str, str]]:
    """Les sections numérotées du guide : {numéro: (titre, texte)}."""
    out: dict[int, tuple[str, str]] = {}
    parts = re.split(r"^(##\s+(\d+)\.?\s*(.*))$", full_guide(), flags=re.MULTILINE)
    # re.split avec groupes : [avant, ligne, numéro, titre, texte, ligne, numéro, titre, texte, ...]
    for i in range(1, len(parts) - 3, 4):
        out[int(parts[i + 1])] = (parts[i + 2].strip(), parts[i + 3].strip())
    return out


def table_of_contents() -> str:
    found = sections()
    if not found:
        return "(guide indisponible)"
    return "\n".join(f"{n}. {title}" for n, (title, _) in sorted(found.items()))


def read_section(number: int) -> str:
    found = sections()
    if number == 0 or number not in found:
        return "Sommaire du guide (appelle lire_guide avec le numéro d'une section) :\n" + table_of_contents()
    title, text = found[number]
    return f"## {number}. {title}\n\n{text}"
