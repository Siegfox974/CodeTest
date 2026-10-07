"""Serveur web local : sert l'écran de chat et diffuse les événements de la salle."""

from __future__ import annotations

import json
import os
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .events import EventBus
from .feed import DEFAULT_UNIVERSE, MultiExchangeFeed, SimulatedFeed
from .notebook import Notebook
from .room import Settings, TradingRoom

STATIC = Path(__file__).parent / "static"


class App:
    def __init__(self, notebook_path: Path, runs_dir: Path, feed_factory=None, client=None):
        self.notebook_path = notebook_path
        self.runs_dir = runs_dir
        self.feed_factory = feed_factory
        self.client = client
        self.bus = EventBus()
        self.room: TradingRoom | None = None
        self.lock = threading.Lock()

    def has_api_key(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                    or self.client is not None)

    def start(self, body: dict) -> dict:
        with self.lock:
            if self.room and not self.room.stopping.is_set():
                raise ValueError("une séance est déjà en cours")
            capital = float(body.get("capital", 0))
            if capital <= 0:
                raise ValueError("indique un montant de départ positif")
            mode = body.get("mode", "claude")
            if mode == "claude":
                try:
                    import anthropic  # noqa: F401
                except ImportError:
                    raise ValueError("le mode Claude nécessite `pip install anthropic`")
            demo = mode == "demo"
            settings = Settings(
                capital=capital,
                mode=mode,
                fee_rate=float(body.get("fee_pct", 0.1)) / 100,
                min_exposure=float(body.get("min_exposure_pct", 50)) / 100,
                max_strikes=int(body.get("max_strikes", 3)),
                cycle_seconds=float(body.get("cycle_minutes", 0.25 if demo else 5)) * 60,
                tick_seconds=float(body.get("tick_seconds", 2 if demo else 30)),
                effort=body.get("effort", "medium"),
                max_searches=int(body.get("max_searches", 3)),
                max_generations=int(body.get("max_generations", 0)),
                universe=body.get("universe") or list(DEFAULT_UNIVERSE),
            )
            if self.feed_factory:
                feed = self.feed_factory(settings)
            elif body.get("market", "real") == "real":
                feed = MultiExchangeFeed(settings.universe)
            else:
                feed = SimulatedFeed(settings.universe, volatility=0.002)
            stamp = time.strftime("%Y%m%d-%H%M%S")
            self.bus = EventBus(self.runs_dir / f"salle-{stamp}.jsonl")
            self.room = TradingRoom(settings, feed, self.bus, Notebook(self.notebook_path), self.client)
            self.room.start()
            return {"ok": True}

    def stop(self) -> dict:
        if self.room:
            self.room.stop()
        return {"ok": True}

    def state(self) -> dict:
        running = bool(self.room and not self.room.stopping.is_set())
        return {"running": running, "has_api_key": self.has_api_key(), "universe": DEFAULT_UNIVERSE,
                "events": len(self.bus.events)}


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _json(self, data: object, status: int = 200) -> None:
            body = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path in ("/", "/index.html"):
                body = (STATIC / "index.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif url.path == "/api/state":
                self._json(app.state())
            elif url.path == "/api/events":
                after = int(parse_qs(url.query).get("after", ["-1"])[0])
                bus = app.bus
                self._json({"bus": id(bus), "events": bus.since(after, timeout=20.0)})
            else:
                self._json({"error": "introuvable"}, 404)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            try:
                if self.path == "/api/start":
                    self._json(app.start(body))
                elif self.path == "/api/stop":
                    self._json(app.stop())
                else:
                    self._json({"error": "introuvable"}, 404)
            except ValueError as e:
                self._json({"error": str(e)}, 400)

    return Handler


def serve(host: str = "127.0.0.1", port: int = 8765, notebook: str = "carnet/carnet.json",
          runs_dir: str = "runs", open_browser: bool = True, app: App | None = None) -> None:
    app = app or App(Path(notebook), Path(runs_dir))
    server = ThreadingHTTPServer((host, port), make_handler(app))
    url = f"http://{host}:{port}"
    print(f"Salle des marchés ouverte sur {url}  (Ctrl+C pour fermer)")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.stop()
        server.server_close()
