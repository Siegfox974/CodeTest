"""Bus d'événements : tout ce qui se passe dans la salle est publié ici, puis diffusé à l'interface."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path


class EventBus:
    def __init__(self, log_path: str | Path | None = None):
        self.events: list[dict] = []
        self.cond = threading.Condition()
        self.log_path = Path(log_path) if log_path else None
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def publish(self, kind: str, **data) -> dict:
        with self.cond:
            event = {"id": len(self.events), "kind": kind, "ts": time.time(), **data}
            self.events.append(event)
            if self.log_path:
                with self.log_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(event, ensure_ascii=False) + "\n")
            self.cond.notify_all()
            return event

    def since(self, last_id: int, timeout: float = 15.0) -> list[dict]:
        """Événements postérieurs à last_id ; attend jusqu'à `timeout` s'il n'y en a pas."""
        with self.cond:
            if len(self.events) <= last_id + 1:
                self.cond.wait(timeout)
            return self.events[last_id + 1:]

    # raccourcis pour les messages du chat
    def say(self, who: dict, text: str, role: str) -> dict:
        return self.publish("message", author=who, role=role, text=text)

    def thought(self, who: dict, text: str, role: str) -> dict:
        return self.publish("thought", author=who, role=role, text=text)

    def action(self, who: dict, icon: str, text: str, role: str, detail: object = None) -> dict:
        return self.publish("action", author=who, role=role, icon=icon, text=text, detail=detail)

    def system(self, text: str, tone: str = "info") -> dict:
        return self.publish("system", text=text, tone=tone)
