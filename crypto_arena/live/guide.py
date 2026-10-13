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


def read_section(number: int, finding: int = 0) -> str:
    """Une section coûte cher à lire en entier : par défaut, ses règles et le sommaire de ses constats ;
    un constat n'est renvoyé en détail que sur demande."""
    found = sections()
    if number == 0 or number not in found:
        return "Sommaire du guide (appelle lire_guide avec le numéro d'une section) :\n" + table_of_contents()
    title, text = found[number]
    rules, _, details = text.partition("### Constats détaillés")
    blocks = re.split(r"(?=^\*\*\d+\.\d+ )", details, flags=re.MULTILINE)
    findings = [b.strip() for b in blocks if b.strip().startswith("**")]
    if finding:
        if not 1 <= finding <= len(findings):
            return f"La section {number} compte {len(findings)} constats (1 à {len(findings)})."
        return f"## {number}. {title} — constat {number}.{finding}\n\n{findings[finding - 1]}"
    index = "\n".join(f"- {number}.{i} " + re.sub(r"^\*\*\d+\.\d+ |\*\*.*$", "", f.splitlines()[0])
                      for i, f in enumerate(findings, 1))
    return (f"## {number}. {title}\n\n{rules.strip()}\n\n### Constats (lis-en un avec lire_guide(section={number}, "
            f"constat=N))\n{index}")
