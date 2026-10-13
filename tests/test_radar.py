import tempfile
import time
import unittest
from email.utils import formatdate
from pathlib import Path

from crypto_arena.live.config import ApiConfig
from crypto_arena.live.events import EventBus
from crypto_arena.live.feed import SimulatedFeed
from crypto_arena.live.news import Radar, parse_feed
from crypto_arena.live.notebook import Notebook
from crypto_arena.live.personas import Persona
from crypto_arena.live.room import Settings, TradingRoom
from crypto_arena.live.tools import TraderTools

NOW = formatdate(time.time() - 600)
RSS = f"""<?xml version="1.0"?><rss version="2.0"><channel><title>CoinDesk</title>
<item><title>Bitcoin ETF inflows hit record as BTC rallies</title><link>https://www.coindesk.com/a</link>
<pubDate>{NOW}</pubDate><description>&lt;p&gt;Spot bitcoin ETFs saw &lt;b&gt;record&lt;/b&gt; inflows.&lt;/p&gt;</description></item>
<item><title>Opinion: what I had for breakfast</title><link>javascript:alert(1)</link><pubDate>{NOW}</pubDate></item>
</channel></rss>"""
ATOM = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>The Block</title>
<entry><title>Solana network suffers exploit</title><link href="https://www.theblock.co/b"/>
<updated>2099-01-01T00:00:00Z</updated><summary>An exploit on a Solana DeFi protocol.</summary></entry></feed>"""

JSON = {
    "api.alternative.me/fng": {"data": [{"value": "22", "value_classification": "Extreme Fear"},
                                        {"value": "35", "value_classification": "Fear"}]},
    "coingecko.com/api/v3/search/trending": {"coins": [{"item": {"name": "Pepe", "symbol": "PEPE", "market_cap_rank": 30}}]},
    "fapi.binance.com/fapi/v1/premiumIndex": [{"symbol": "BTCUSDT", "lastFundingRate": "0.00010000"},
                                              {"symbol": "XYZUSDT", "lastFundingRate": "0.5"}],
    "reddit.com/r/CryptoCurrency/hot.json": {"data": {"children": [
        {"data": {"title": "Daily discussion", "permalink": "/r/c/1", "created_utc": time.time(), "score": 9999, "stickied": True}},
        {"data": {"title": "ETH just broke 4k", "permalink": "/r/c/2", "created_utc": time.time() - 60, "score": 1200,
                  "selftext": "wow"}}]}},
    "api.x.com/2/tweets/search/recent": {
        "data": [{"id": "1", "text": "Huge $SOL news https://t.co/x", "author_id": "u1", "created_at": "2026-10-13T10:00:00Z",
                  "public_metrics": {"like_count": 300, "retweet_count": 40}}],
        "includes": {"users": [{"id": "u1", "username": "whale", "public_metrics": {"followers_count": 5000}}]}},
}
TEXT = {"coindesk.com": RSS, "theblock.co": ATOM}
FEEDS = [{"name": "CoinDesk", "url": "https://www.coindesk.com/rss", "enabled": True},
         {"name": "The Block", "url": "https://www.theblock.co/rss.xml", "enabled": True},
         {"name": "Mort", "url": "https://mort.example/rss", "enabled": True}]


def fake_get(url, timeout=6.0, headers=None):
    if "api.x.com" in url and (headers or {}).get("Authorization") != "Bearer tok-123456789":
        raise OSError("HTTP Error 401: Unauthorized")
    for key, payload in JSON.items():
        if key in url:
            return payload
    raise OSError("HTTP Error 404: Not Found")


def fake_text(url, timeout=6.0, headers=None):
    for key, payload in TEXT.items():
        if key in url:
            return payload
    raise OSError("timed out")


def radar(**kw):
    return Radar(["BTC", "ETH", "SOL"], FEEDS, get=fake_get, get_text=fake_text, **kw)


class FeedParsingTest(unittest.TestCase):
    def test_rss_and_atom(self):
        rss = parse_feed(RSS, "CoinDesk")
        self.assertEqual(rss[0].title, "Bitcoin ETF inflows hit record as BTC rallies")
        self.assertEqual(rss[0].summary, "Spot bitcoin ETFs saw record inflows.")
        self.assertEqual(rss[1].url, "")              # lien javascript: refusé
        atom = parse_feed(ATOM, "The Block")
        self.assertEqual(atom[0].url, "https://www.theblock.co/b")


class RadarTest(unittest.TestCase):
    def test_poll_collects_news_sentiment_and_flags_hot_items(self):
        r = radar()
        hot = r.poll(deadline=3)
        titles = {i.title for i in hot}
        self.assertIn("Bitcoin ETF inflows hit record as BTC rallies", titles)
        self.assertIn("ETH just broke 4k", titles)                 # Reddit très voté sur un actif suivi
        self.assertNotIn("Opinion: what I had for breakfast", titles)
        self.assertNotIn("Daily discussion", {i.title for i in r.items.values()})   # sujet épinglé ignoré
        self.assertEqual(r.sentiment["fear_greed"], {"valeur": 22, "humeur": "Extreme Fear", "veille": 35})
        self.assertEqual(r.sentiment["financement_pct"], {"BTC": 0.01})
        self.assertEqual(r.status["presse:Mort"].split(":")[0], "OSError")
        self.assertEqual(r.poll(deadline=3), [])                   # rien de nouveau au relevé suivant
        self.assertIn("Fear & Greed : 22/100", r.headlines_text())

    def test_filters_and_x_search(self):
        r = radar(x_token="tok-123456789", x_every=0)
        r.poll(deadline=3)
        self.assertEqual(r.x_reads, 1)
        self.assertTrue(all("BTC" in i.assets or "btc" in i.title.lower() for i in r.latest("BTC")))
        tweet = [i for i in r.items.values() if i.kind == "x"][0]
        self.assertEqual(tweet.url, "https://x.com/whale/status/1")
        self.assertEqual(tweet.score, 380)
        with self.assertRaises(LookupError):
            radar().search_x("bitcoin")


class RadarInRoomTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def test_trader_tools_and_briefing(self):
        r = radar(x_token="tok-123456789")
        r.poll(deadline=3)
        s = Settings(capital=100.0, mode="demo", seed=1, demo_pace=0)
        room = TradingRoom(s, SimulatedFeed(seed=1), EventBus(), Notebook(self.dir / "c.json"), radar=r)
        room.feed.refresh()
        room.trader = room._seat_trader(Persona("Zoé", "🐧", "#4fc3f7", "méthodique"))
        room.supervisor = room._hire_supervisor()
        tools = TraderTools(room, room.trader)
        news, err = tools.call("actualites", {"filtre": "BTC", "nombre": 5})
        self.assertFalse(err)
        self.assertEqual(news[0]["actifs"], ["BTC"])
        mood, err = tools.call("sentiment_marche", {})
        self.assertEqual(mood["fear_greed"]["valeur"], 22)
        tweets, err = tools.call("chercher_sur_x", {"requete": "$SOL"})
        self.assertFalse(err)
        self.assertEqual(tweets[0]["auteur"], "X @whale (5000 abonnés)")
        brief = room.briefing(room.trader)
        self.assertIn("Veille de Radar", brief)
        self.assertIn("https://www.coindesk.com/a", brief)   # le lien rend l'article lisible par web_fetch

    def test_x_without_token_suggests_web_search(self):
        s = Settings(capital=100.0, mode="demo", seed=1)
        room = TradingRoom(s, SimulatedFeed(seed=1), EventBus(), Notebook(self.dir / "c.json"), radar=radar())
        room.feed.refresh()
        room.trader = room._seat_trader(Persona("Zoé", "🐧", "#4fc3f7", "méthodique"))
        result, err = TraderTools(room, room.trader).call("chercher_sur_x", {"requete": "btc"})
        self.assertTrue(err)
        self.assertIn("site:x.com", result)


class NewsConfigTest(unittest.TestCase):
    def test_settings_roundtrip_and_test(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = ApiConfig(Path(d) / "apis.json")
            cfg.update({"veille": {"flux": FEEDS[:2], "x_token": "tok-123456789", "x_toutes_les_min": 2}})
            cfg = ApiConfig(Path(d) / "apis.json")
            self.assertEqual(cfg.public()["veille"]["x_hint"], "…6789")
            self.assertNotIn("tok-123456789", str(cfg.public()))
            result = cfg.test(get=fake_get, get_text=fake_text, symbols=("BTC",), anthropic_client=None)
            by = {r["name"]: r for r in result["veille"]}
            self.assertTrue(by["CoinDesk"]["ok"])
            self.assertEqual(by["CoinDesk"]["detail"], "2 articles")
            self.assertEqual(by["X"]["detail"], "1 tweet")
            self.assertTrue(by["X"]["ok"])
            with self.assertRaises(ValueError):
                cfg.update({"veille": {"flux": [{"name": "x", "url": "ftp://bad"}]}})


if __name__ == "__main__":
    unittest.main()
