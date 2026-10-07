"""Le carnet de la lignée : des notes laissées aux successeurs, qui les confirment, les contestent ou les corrigent."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

VERDICTS = ["confirme", "conteste", "corrige"]


class Notebook:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.lock = threading.Lock()
        self.notes: list[dict] = json.loads(self.path.read_text()) if self.path.exists() else []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.notes, ensure_ascii=False, indent=2))
        tmp.replace(self.path)

    @staticmethod
    def status(note: dict) -> str:
        reviews = note["avis"]
        if not reviews:
            return "non vérifiée"
        last = reviews[-1]["verdict"]
        if last == "corrige":
            return "corrigée"
        if last == "conteste":
            return "contestée"
        return f"confirmée ×{sum(r['verdict'] == 'confirme' for r in reviews)}"

    @staticmethod
    def current_text(note: dict) -> str:
        for review in reversed(note["avis"]):
            if review["verdict"] == "corrige" and review.get("correction"):
                return review["correction"]
        return note["texte"]

    def view(self) -> list[dict]:
        with self.lock:
            return [{
                "id": n["id"], "auteur": n["auteur"], "statut": self.status(n),
                "texte": self.current_text(n), "texte_original": n["texte"],
                "sources": n["sources"], "avis": n["avis"],
            } for n in self.notes]

    def add(self, author: str, text: str, sources: list[str]) -> dict:
        with self.lock:
            note = {"id": max((n["id"] for n in self.notes), default=0) + 1, "auteur": author,
                    "date": time.strftime("%Y-%m-%d %H:%M"), "texte": text.strip(),
                    "sources": [s for s in sources if s], "avis": []}
            self.notes.append(note)
            self._save()
            return note

    def review(self, author: str, note_id: int, verdict: str, comment: str, correction: str = "") -> dict:
        if verdict not in VERDICTS:
            raise ValueError(f"verdict inconnu {verdict}, choisir parmi {VERDICTS}")
        with self.lock:
            note = next((n for n in self.notes if n["id"] == note_id), None)
            if note is None:
                raise ValueError(f"aucune note n°{note_id}")
            if verdict == "corrige" and not correction.strip():
                raise ValueError("une correction doit fournir le texte corrigé")
            note["avis"].append({"auteur": author, "verdict": verdict, "commentaire": comment.strip(),
                                 "correction": correction.strip(), "date": time.strftime("%Y-%m-%d %H:%M")})
            self._save()
            return note
