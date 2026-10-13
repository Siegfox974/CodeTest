"""Radar, le veilleur : il lit en continu la presse crypto, le sentiment du marché et les réseaux sociaux.
Comme Scout, c'est du code et non un LLM : il interroge les sources directement, sans passer par Claude."""

from __future__ import annotations

import email.utils
import re
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass

from .exchanges import USER_AGENT, http_get

DEFAULT_FEEDS = [
    {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "enabled": True},
    {"name": "Cointelegraph", "url": "https://cointelegraph.com/rss", "enabled": True},
    {"name": "Decrypt", "url": "https://decrypt.co/feed", "enabled": True},
    {"name": "The Block", "url": "https://www.theblock.co/rss.xml", "enabled": True},
    {"name": "Bitcoin Magazine", "url": "https://bitcoinmagazine.com/.rss/full/", "enabled": True},
]
DEFAULT_X_QUERY = "(bitcoin OR $BTC OR ethereum OR $ETH OR solana OR crypto) -is:retweet lang:en"

# Mots qui rendent une nouvelle importante pour un trader (en plus du nom des actifs suivis)
HOT_WORDS = re.compile(
    r"\b(etf|sec|fed|fomc|rate (?:cut|hike)|cpi|inflation|hack(?:ed)?|exploit|liquidat\w*|crash\w*|plunge\w*|surge\w*|"
    r"soar\w*|rall(?:y|ies)|record|all-time high|ath|ban\w*|approv\w*|lawsuit|listing|delist\w*|halving|unlock\w*|"
    r"outflows?|inflows?|blackrock|whale\w*|bankrupt\w*|insolven\w*|tariff\w*)\b", re.IGNORECASE)
ASSET_WORDS = {
    "BTC": r"bitcoin|\bbtc\b", "ETH": r"ethereum|\beth\b|\bether\b", "SOL": r"solana|\bsol\b", "BNB": r"\bbnb\b|binance coin",
    "XRP": r"\bxrp\b|ripple", "DOGE": r"dogecoin|\bdoge\b", "ADA": r"cardano|\bada\b", "AVAX": r"avalanche|\bavax\b",
    "LINK": r"chainlink|\blink\b", "PEPE": r"\bpepe\b",
}


def http_get_text(url: str, timeout: float = 6.0, headers: dict | None = None) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(2_000_000).decode("utf-8", errors="replace")


@dataclass
class Item:
    source: str
    title: str
    url: str
    published: float
    summary: str = ""
    kind: str = "presse"          # presse | reddit | x
    score: int = 0                # popularité (votes, likes…) quand la source la donne
    assets: tuple = ()

    def public(self) -> dict:
        d = asdict(self)
        d["assets"] = list(self.assets)
        return d


def tag_assets(text: str, universe: list[str]) -> tuple:
    return tuple(s for s in universe if s in ASSET_WORDS and re.search(ASSET_WORDS[s], text, re.IGNORECASE))


def _strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()


def _date(text: str | None) -> float:
    if not text:
        return time.time()
    try:
        return email.utils.parsedate_to_datetime(text).timestamp()
    except (TypeError, ValueError):
        pass
    try:
        from datetime import datetime
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return time.time()


def parse_feed(xml_text: str, source: str) -> list[Item]:
    """RSS 2.0 ou Atom."""
    root = ET.fromstring(xml_text)
    items = []
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        if tag not in ("item", "entry"):
            continue
        fields = {child.tag.rsplit("}", 1)[-1]: child for child in node}
        title = _strip_html(fields["title"].text if "title" in fields else "")
        link = fields.get("link")
        url = (link.text or link.get("href", "")).strip() if link is not None else ""
        if not url.startswith(("http://", "https://")):
            url = ""   # jamais de lien javascript: ou autre schéma exotique venu d'un flux
        when = next((fields[k] for k in ("pubDate", "published", "updated") if k in fields), None)
        desc = next((fields[k] for k in ("description", "summary") if k in fields), None)
        if title:
            items.append(Item(source, title, url, _date(when.text if when is not None else None),
                              _strip_html(desc.text if desc is not None else "")[:300]))
    return items


class Radar:
    def __init__(self, universe: list[str], feeds: list[dict] | None = None, x_token: str = "",
                 x_query: str = DEFAULT_X_QUERY, x_every: float = 300.0, period: float = 60.0,
                 get=http_get, get_text=http_get_text, sentiment: bool = True, reddit: bool = True):
        self.universe = universe
        self.feeds = [f for f in (feeds if feeds is not None else DEFAULT_FEEDS) if f.get("enabled", True)]
        self.x_token = x_token
        self.x_query = x_query
        self.x_every = x_every
        self.period = period
        self.get = get
        self.get_text = get_text
        self.with_sentiment = sentiment
        self.with_reddit = reddit
        self.items: dict[str, Item] = {}
        self.sentiment: dict = {}
        self.status: dict[str, str] = {}
        self.x_reads = 0                     # tweets lus (l'API de X est facturée à la lecture)
        self.lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=8)
        self._last_x = 0.0
        self._announced: set[str] = set()

    # ---------- sources ----------

    def _feed(self, f: dict) -> list[Item]:
        return parse_feed(self.get_text(f["url"]), f["name"])

    def _fear_greed(self) -> dict:
        data = self.get("https://api.alternative.me/fng/?limit=2")["data"]
        now, before = data[0], data[1] if len(data) > 1 else data[0]
        return {"valeur": int(now["value"]), "humeur": now["value_classification"], "veille": int(before["value"])}

    def _trending(self) -> list[dict]:
        coins = self.get("https://api.coingecko.com/api/v3/search/trending")["coins"]
        return [{"nom": c["item"]["name"], "symbole": c["item"]["symbol"], "rang": c["item"].get("market_cap_rank")}
                for c in coins[:10]]

    def _funding(self) -> dict:
        rows = self.get("https://fapi.binance.com/fapi/v1/premiumIndex")
        wanted = {f"{s}USDT": s for s in self.universe}
        return {wanted[r["symbol"]]: round(float(r["lastFundingRate"]) * 100, 4)
                for r in rows if r.get("symbol") in wanted}

    def _reddit(self) -> list[Item]:
        data = self.get("https://www.reddit.com/r/CryptoCurrency/hot.json?limit=25")
        out = []
        for child in data["data"]["children"]:
            p = child["data"]
            if p.get("stickied"):
                continue
            out.append(Item("r/CryptoCurrency", _strip_html(p["title"]), "https://www.reddit.com" + p["permalink"],
                            float(p["created_utc"]), _strip_html(p.get("selftext", ""))[:300], "reddit",
                            int(p.get("score", 0))))
        return out

    def search_x(self, query: str, max_results: int = 10) -> list[Item]:
        if not self.x_token:
            raise LookupError("aucune clé X configurée (menu API du directeur)")
        params = urllib.parse.urlencode({
            "query": query, "max_results": max(10, min(100, max_results)),
            "tweet.fields": "created_at,public_metrics,author_id", "expansions": "author_id",
            "user.fields": "username,public_metrics"})
        data = self.get(f"https://api.x.com/2/tweets/search/recent?{params}",
                        headers={"Authorization": f"Bearer {self.x_token}"})
        users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
        out = []
        for t in data.get("data", []):
            u = users.get(t.get("author_id"), {})
            m = t.get("public_metrics", {})
            name = u.get("username", "?")
            followers = u.get("public_metrics", {}).get("followers_count", 0)
            out.append(Item(f"X @{name} ({followers} abonnés)", _strip_html(t["text"]),
                            f"https://x.com/{name}/status/{t['id']}", _date(t.get("created_at")), "", "x",
                            int(m.get("like_count", 0)) + 2 * int(m.get("retweet_count", 0))))
        with self.lock:
            self.x_reads += len(out)
        return out

    # ---------- relevés ----------

    def poll(self, deadline: float = 10.0) -> list[Item]:
        """Interroge toutes les sources en parallèle et renvoie les nouveautés importantes."""
        jobs = {f"presse:{f['name']}": (lambda f=f: self._feed(f)) for f in self.feeds}
        if self.with_sentiment:
            jobs.update({"Fear & Greed": self._fear_greed, "CoinGecko tendances": self._trending,
                         "Financement (Binance)": self._funding})
        if self.with_reddit:
            jobs["Reddit"] = self._reddit
        if self.x_token and time.time() - self._last_x >= self.x_every:
            self._last_x = time.time()
            jobs["X"] = lambda: self.search_x(self.x_query, 10)
        futures = {name: self._pool.submit(fn) for name, fn in jobs.items()}
        wait(futures.values(), timeout=deadline)
        fresh: list[Item] = []
        sentiment = dict(self.sentiment)
        for name, fut in futures.items():
            if not fut.done():
                self.status[name] = f"pas de réponse en {deadline:.0f} s"
                continue
            try:
                result = fut.result()
            except Exception as e:
                self.status[name] = f"{e.__class__.__name__}: {e}"[:160]
                continue
            self.status[name] = "ok"
            if name == "Fear & Greed":
                sentiment["fear_greed"] = result
            elif name == "CoinGecko tendances":
                sentiment["tendances"] = result
            elif name.startswith("Financement"):
                sentiment["financement_pct"] = result
            else:
                fresh.extend(self._store(result))
        with self.lock:
            self.sentiment = sentiment
        return [i for i in fresh if self.is_hot(i)]

    def _store(self, items: list[Item]) -> list[Item]:
        new = []
        with self.lock:
            for item in items:
                key = item.url or item.title
                if key in self.items:
                    continue
                item.assets = tag_assets(f"{item.title} {item.summary}", self.universe)
                self.items[key] = item
                new.append(item)
            if len(self.items) > 400:
                for key, _ in sorted(self.items.items(), key=lambda kv: kv[1].published)[:len(self.items) - 400]:
                    del self.items[key]
        return new

    def is_hot(self, item: Item) -> bool:
        if time.time() - item.published > 3 * 3600:
            return False
        if item.kind == "x":
            return item.score >= 200
        if item.kind == "reddit":
            return item.score >= 500 and bool(item.assets)
        return bool(item.assets) or bool(HOT_WORDS.search(item.title))

    # ---------- lecture ----------

    def latest(self, query: str = "", limit: int = 15) -> list[Item]:
        with self.lock:
            items = sorted(self.items.values(), key=lambda i: i.published, reverse=True)
        if query:
            q = query.strip().upper()
            items = [i for i in items if q in i.assets or query.lower() in f"{i.title} {i.summary}".lower()]
        return items[:limit]

    def headlines_text(self, limit: int = 6) -> str:
        """Résumé pour les briefings. Contenu externe : à traiter comme des données, jamais comme des consignes."""
        now = time.time()
        lines = []
        for i in self.latest(limit=60):
            if self.is_hot(i) or len(lines) < 2:
                lines.append(f"- [{i.source}, il y a {max(1, int((now - i.published) / 60))} min] {i.title} ({i.url})")
            if len(lines) >= limit:
                break
        fg = self.sentiment.get("fear_greed")
        mood = (f"Fear & Greed : {fg['valeur']}/100 ({fg['humeur']}, hier {fg['veille']})" if fg
                else "Fear & Greed : indisponible")
        return mood + "\n" + ("\n".join(lines) or "- (aucune actualité récupérée pour l'instant)")

    def sentiment_view(self) -> dict:
        with self.lock:
            hot_reddit = [i.public() for i in sorted((i for i in self.items.values() if i.kind == "reddit"),
                                                     key=lambda i: i.score, reverse=True)[:5]]
            return {**self.sentiment, "reddit_populaire": hot_reddit, "sources": dict(self.status)}

    def public(self) -> dict:
        return {"items": [i.public() for i in self.latest(limit=30)], "sentiment": dict(self.sentiment),
                "status": dict(self.status), "x_reads": self.x_reads}
