"""Configuration des sources : bourses intégrées activées, API ajoutées à la main, clé Anthropic, et test rapide."""

from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .exchanges import ALL_EXCHANGES, CustomExchange, http_get
from .news import DEFAULT_FEEDS, DEFAULT_X_QUERY, Radar, http_get_text

BUILTIN = [cls.name for cls in ALL_EXCHANGES]


class ApiConfig:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.lock = threading.Lock()
        data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.enabled: dict[str, bool] = {n: data.get("exchanges", {}).get(n, True) for n in BUILTIN}
        self.custom: list[dict] = data.get("custom", [])
        self.anthropic_api_key: str = data.get("anthropic_api_key", "")
        news = data.get("veille", {})
        self.news_enabled: bool = news.get("active", True)
        self.feeds: list[dict] = news.get("flux", [dict(f) for f in DEFAULT_FEEDS])
        self.sentiment: bool = news.get("sentiment", True)
        self.reddit: bool = news.get("reddit", True)
        self.x_token: str = news.get("x_token", "")
        self.x_query: str = news.get("x_requete", DEFAULT_X_QUERY)
        self.x_every_min: float = float(news.get("x_toutes_les_min", 5))
        self.last_test: dict | None = None

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        news = {"active": self.news_enabled, "flux": self.feeds, "sentiment": self.sentiment, "reddit": self.reddit,
                "x_token": self.x_token, "x_requete": self.x_query, "x_toutes_les_min": self.x_every_min}
        tmp.write_text(json.dumps({"exchanges": self.enabled, "custom": self.custom,
                                   "anthropic_api_key": self.anthropic_api_key, "veille": news},
                                  ensure_ascii=False, indent=2), encoding="utf-8")
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
            news = body.get("veille")
            if news is not None:
                self.news_enabled = bool(news.get("active", self.news_enabled))
                self.sentiment = bool(news.get("sentiment", self.sentiment))
                self.reddit = bool(news.get("reddit", self.reddit))
                if "flux" in news:
                    feeds = []
                    for f in news["flux"]:
                        entry = {"name": str(f.get("name", "")).strip(), "url": str(f.get("url", "")).strip(),
                                 "enabled": bool(f.get("enabled", True))}
                        if not entry["name"] or not entry["url"].startswith(("http://", "https://")):
                            raise ValueError("chaque flux doit avoir un nom et une URL en http(s)://")
                        if entry["name"] in [x["name"] for x in feeds]:
                            raise ValueError(f"le flux « {entry['name']} » existe déjà")
                        feeds.append(entry)
                    self.feeds = feeds
                if news.get("x_requete"):
                    self.x_query = str(news["x_requete"]).strip()[:500]
                if news.get("x_toutes_les_min"):
                    self.x_every_min = max(1.0, float(news["x_toutes_les_min"]))
                if news.get("clear_x_token"):
                    self.x_token = ""
                elif news.get("x_token"):
                    self.x_token = str(news["x_token"]).strip()
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
            "veille": {"active": self.news_enabled, "flux": self.feeds, "sentiment": self.sentiment,
                       "reddit": self.reddit, "x_configure": bool(self.x_token),
                       "x_hint": f"…{self.x_token[-4:]}" if len(self.x_token) > 8 else "",
                       "x_requete": self.x_query, "x_toutes_les_min": self.x_every_min},
            "last_test": self.last_test,
        }

    def radar(self, universe: list[str], get=http_get, get_text=http_get_text) -> Radar | None:
        if not self.news_enabled:
            return None
        return Radar(universe, self.feeds, self.x_token, self.x_query, self.x_every_min * 60,
                     get=get, get_text=get_text, sentiment=self.sentiment, reddit=self.reddit)

    def exchanges(self, only: list[str] | None = None, get=http_get) -> list:
        """Les sources actives (ou seulement celles de `only`), prêtes à être interrogées."""
        sources = [cls(get) for cls in ALL_EXCHANGES if self.enabled.get(cls.name)]
        for c in self.custom:
            sources.append(CustomExchange(c["name"], c["url"], c["symbol_format"], c["price_path"], c["headers"], get))
        if only:
            sources = [s for s in sources if s.name in only]
        return sources

    def _test_news(self, get, get_text) -> list[dict]:
        radar = self.radar(["BTC", "ETH"], get=get, get_text=get_text)
        if radar is None:
            return []
        radar.x_every = 0          # le test interroge X une fois (≈ 10 lectures facturées) si une clé est configurée
        radar.poll(deadline=8.0)
        counts: dict[str, int] = {}
        for item in radar.items.values():
            key = "X" if item.kind == "x" else "Reddit" if item.kind == "reddit" else f"presse:{item.source}"
            counts[key] = counts.get(key, 0) + 1
        def detail(name: str, state: str) -> str:
            if state != "ok":
                return state
            n = counts.get(name, 0)
            unit = {"X": "tweet", "Reddit": "sujet"}.get(name, "article" if name.startswith("presse:") else "")
            return f"{n} {unit}{'s' if n > 1 else ''}" if unit else "ok"

        return [{"name": name.removeprefix("presse:"), "ok": state == "ok", "detail": detail(name, state)}
                for name, state in radar.status.items()]

    def test(self, get=http_get, symbols: tuple = ("BTC", "ETH"), model: str = "claude-opus-5-5",
             anthropic_client=None, get_text=http_get_text) -> dict:
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
            news = pool.submit(self._test_news, get, get_text)
            result = {"at": time.time(), "sources": [f.result() for f in futures], "anthropic": claude.result(),
                      "veille": news.result()}
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
