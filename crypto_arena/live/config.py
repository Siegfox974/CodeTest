"""Configuration des sources : bourses intégrées activées, API ajoutées à la main, clé Anthropic, et test rapide."""

from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .exchanges import ALL_EXCHANGES, CustomExchange, http_get

BUILTIN = [cls.name for cls in ALL_EXCHANGES]


class ApiConfig:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.lock = threading.Lock()
        data = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.enabled: dict[str, bool] = {n: data.get("exchanges", {}).get(n, True) for n in BUILTIN}
        self.custom: list[dict] = data.get("custom", [])
        self.anthropic_api_key: str = data.get("anthropic_api_key", "")
        self.last_test: dict | None = None

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"exchanges": self.enabled, "custom": self.custom,
                                   "anthropic_api_key": self.anthropic_api_key}, ensure_ascii=False, indent=2))
        os.chmod(tmp, 0o600)
        tmp.replace(self.path)

    def update(self, body: dict) -> None:
        with self.lock:
            for name, on in (body.get("exchanges") or {}).items():
                if name in self.enabled:
                    self.enabled[name] = bool(on)
            if "custom" in body:
                custom = []
                for c in body["custom"]:
                    entry = {"name": str(c.get("name", "")).strip(), "url": str(c.get("url", "")).strip(),
                             "symbol_format": str(c.get("symbol_format") or "{SYM}USDT").strip(),
                             "price_path": str(c.get("price_path") or "price").strip(),
                             "headers": {k: str(v) for k, v in (c.get("headers") or {}).items()}}
                    if not entry["name"]:
                        raise ValueError("chaque API doit avoir un nom")
                    if entry["name"] in BUILTIN or entry["name"] in [x["name"] for x in custom]:
                        raise ValueError(f"le nom « {entry['name']} » est déjà pris")
                    CustomExchange(entry["name"], entry["url"])  # valide l'URL
                    custom.append(entry)
                self.custom = custom
            if body.get("clear_anthropic_api_key"):
                self.anthropic_api_key = ""
            elif body.get("anthropic_api_key"):
                self.anthropic_api_key = str(body["anthropic_api_key"]).strip()
            self.save()

    def anthropic_key(self) -> str:
        return self.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    def public(self) -> dict:
        key = self.anthropic_key()
        return {
            "exchanges": [{"name": n, "enabled": on} for n, on in self.enabled.items()],
            "custom": self.custom,
            "anthropic": {"configured": bool(key or os.environ.get("ANTHROPIC_AUTH_TOKEN")),
                          "hint": f"…{key[-4:]}" if len(key) > 8 else "",
                          "source": "menu" if self.anthropic_api_key else ("environnement" if key else "")},
            "last_test": self.last_test,
        }

    def exchanges(self, only: list[str] | None = None, get=http_get) -> list:
        """Les sources actives (ou seulement celles de `only`), prêtes à être interrogées."""
        sources = [cls(get) for cls in ALL_EXCHANGES if self.enabled.get(cls.name)]
        for c in self.custom:
            sources.append(CustomExchange(c["name"], c["url"], c["symbol_format"], c["price_path"], c["headers"], get))
        if only:
            sources = [s for s in sources if s.name in only]
        return sources

    def test(self, get=http_get, symbols: tuple = ("BTC", "ETH"), model: str = "claude-opus-5-5",
             anthropic_client=None) -> dict:
        """Interroge chaque source en parallèle et vérifie la clé Anthropic."""
        def probe(ex) -> dict:
            t0 = time.monotonic()
            try:
                quotes = ex.tickers(list(symbols))
                if not quotes:
                    raise LookupError("aucun prix pour " + ", ".join(symbols))
                return {"name": ex.name, "ok": True, "ms": round((time.monotonic() - t0) * 1000),
                        "prices": {s: q.last for s, q in quotes.items()}}
            except Exception as e:
                return {"name": ex.name, "ok": False, "ms": round((time.monotonic() - t0) * 1000),
                        "error": f"{e.__class__.__name__}: {e}"[:200]}

        sources = self.exchanges(get=get)
        with ThreadPoolExecutor(max_workers=max(1, len(sources)) + 1) as pool:
            futures = [pool.submit(probe, ex) for ex in sources]
            claude = pool.submit(self._test_anthropic, model, anthropic_client)
            result = {"at": time.time(), "sources": [f.result() for f in futures], "anthropic": claude.result()}
        self.last_test = result
        return result

    def _test_anthropic(self, model: str, client=None) -> dict:
        if client is None:
            key = self.anthropic_key()
            if not key and not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
                return {"ok": False, "detail": "aucune clé : seul le mode démo est disponible"}
            try:
                import anthropic
            except ImportError:
                return {"ok": False, "detail": "SDK absent : pip install anthropic"}
            client = anthropic.Anthropic(api_key=key or None, max_retries=0, timeout=15)
        try:
            info = client.models.retrieve(model)
            return {"ok": True, "detail": f"clé valide, modèle {getattr(info, 'display_name', model)} accessible"}
        except Exception as e:
            return {"ok": False, "detail": f"{e.__class__.__name__}: {e}"[:200]}
