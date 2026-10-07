import unittest

from crypto_arena.live.exchanges import OKX, Binance, Bybit, Coinbase, Gate, Kraken, KuCoin
from crypto_arena.live.feed import FeedError, MultiExchangeFeed

# Réponses au format des API publiques de chaque bourse
PAYLOADS = {
    "gateio.ws/api/v4/spot/tickers": [
        {"currency_pair": "BTC_USDT", "last": "60000", "highest_bid": "59990", "lowest_ask": "60010",
         "change_percentage": "1.5", "high_24h": "61000", "low_24h": "59000", "quote_volume": "1000000"},
        {"currency_pair": "ETH_USDT", "last": "3000", "change_percentage": "-2"},
        {"currency_pair": "BTC_ETH", "last": "20"},
    ],
    "gateio.ws/api/v4/spot/candlesticks": [["1700000000", "500", "60100", "60200", "59900", "60000", "0.01", "true"]],
    "gateio.ws/api/v4/spot/order_book": {"bids": [["59990", "1.2"]], "asks": [["60010", "0.8"]]},
    "kraken.com/0/public/Ticker?pair=XBTUSDT": {"error": [], "result": {"XBTUSDT": {
        "a": ["60020", "1", "1"], "b": ["60000", "1", "1"], "c": ["60010", "0.1"], "v": ["10", "20"],
        "h": ["61000", "61500"], "l": ["59000", "58500"], "o": "59500"}}},
    "kraken.com/0/public/Ticker?pair=ETHUSDT": {"error": ["EQuery:Unknown asset pair"]},
    "kraken.com/0/public/Ticker?pair=ETHUSD": {"error": [], "result": {"XETHZUSD": {
        "a": ["3001", "1", "1"], "b": ["2999", "1", "1"], "c": ["3000", "1"], "v": ["1", "2"],
        "h": ["1", "3100"], "l": ["1", "2900"], "o": "3000"}}},
    "kraken.com/0/public/Ticker?pair=SOL": {"error": ["EQuery:Unknown asset pair"]},
    "kraken.com/0/public/OHLC": {"error": [], "result": {
        "XBTUSDT": [[1700000000, "60000", "60200", "59900", "60100", "60050", "3.5", 10]], "last": 1700000000}},
    "okx.com/api/v5/market/tickers": {"code": "0", "data": [
        {"instId": "BTC-USDT", "last": "60050", "bidPx": "60040", "askPx": "60060", "open24h": "59000",
         "high24h": "61000", "low24h": "58000", "volCcy24h": "5000000"}]},
    "okx.com/api/v5/market/candles": {"code": "0", "data": [
        ["1700003600000", "2", "2", "2", "2", "1"], ["1700000000000", "1", "1", "1", "1", "1"]]},
    "bybit.com/v5/market/tickers": {"retCode": 0, "result": {"list": [
        {"symbol": "BTCUSDT", "lastPrice": "60030", "price24hPcnt": "0.012", "turnover24h": "9000000"}]}},
    "kucoin.com/api/v1/market/allTickers": {"code": "200000", "data": {"ticker": [
        {"symbol": "BTC-USDT", "last": "75000", "changeRate": "0.01"}]}},  # cotation aberrante
    "coinbase.com/products/BTC-USD/ticker": {"price": "60020", "bid": "60010", "ask": "60030"},
    "coinbase.com/products/BTC-USD/candles": [[1700003600, 1, 3, 2, 2.5, 7], [1700000000, 1, 2, 1.5, 1.8, 5]],
    "binance.vision/api/v3/ticker/24hr": [{"symbol": "BTCUSDT", "lastPrice": "60040", "priceChangePercent": "1.2"}],
}


def fake_get(url, timeout=10.0):
    for key in sorted(PAYLOADS, key=len, reverse=True):
        if key in url:
            return PAYLOADS[key]
    raise OSError(f"404 introuvable : {url}")


def failing_get(url, timeout=10.0):
    raise OSError("Tunnel connection failed: 403 Forbidden")


class ParserTest(unittest.TestCase):
    def test_gate(self):
        g = Gate(fake_get)
        q = g.tickers(["BTC", "ETH", "SOL"])
        self.assertEqual(set(q), {"BTC", "ETH"})
        self.assertEqual((q["BTC"].last, q["BTC"].bid, q["BTC"].change_pct), (60000.0, 59990.0, 1.5))
        c = g.candles("BTC", "1h", 10)[0]
        self.assertEqual((c["o"], c["h"], c["l"], c["c"], c["v"]), (60000.0, 60200.0, 59900.0, 60100.0, 500.0))
        self.assertEqual(g.order_book("BTC", 5)["bids"], [[59990.0, 1.2]])

    def test_kraken_aliases_and_usd_fallback(self):
        k = Kraken(fake_get)
        q = k.tickers(["BTC", "ETH", "SOL"])
        self.assertEqual(q["BTC"].last, 60010.0)
        self.assertEqual(q["ETH"].last, 3000.0)
        self.assertEqual(k.pairs, {"BTC": "XBTUSDT", "ETH": "ETHUSD"})
        self.assertIn("SOL", k.unsupported)
        self.assertEqual(k.candles("BTC", "1h", 5)[0]["c"], 60100.0)

    def test_okx_bybit_kucoin_coinbase_binance(self):
        self.assertAlmostEqual(OKX(fake_get).tickers(["BTC"])["BTC"].change_pct, (60050 / 59000 - 1) * 100)
        self.assertEqual([c["c"] for c in OKX(fake_get).candles("BTC", "1h", 5)], [1.0, 2.0])
        self.assertAlmostEqual(Bybit(fake_get).tickers(["BTC"])["BTC"].change_pct, 1.2)
        self.assertEqual(KuCoin(fake_get).tickers(["BTC"])["BTC"].last, 75000.0)
        cb = Coinbase(fake_get)
        self.assertEqual(cb.tickers(["BTC", "PEPE"])["BTC"].last, 60020.0)
        self.assertIn("PEPE", cb.unsupported)
        self.assertEqual([c["o"] for c in cb.candles("BTC", "1h", 5)], [1.5, 2.0])
        self.assertEqual(Binance(fake_get).tickers(["BTC"])["BTC"].last, 60040.0)


class ConsensusTest(unittest.TestCase):
    def test_median_ignores_outliers_and_tracks_status(self):
        feed = MultiExchangeFeed(["BTC", "ETH"], get=fake_get)
        prices = feed.refresh()
        self.assertNotIn("KuCoin", feed.quotes["BTC"])           # 75 000 $ : écartée
        self.assertTrue(60000 <= prices["BTC"] <= 60050)
        self.assertEqual(feed.status["Gate"], "ok")
        cmp = feed.compare("BTC")
        self.assertLess(cmp["ecart_max_entre_bourses_pct"], 0.1)
        self.assertEqual(feed.candles("BTC", "1h", 5)[-1]["c"], 60100.0)
        self.assertEqual(feed.last_candle_source, "Kraken")
        self.assertEqual(feed.order_book("BTC", 5)[0], "Gate")  # pas de carnet Kraken dans ces données
        self.assertEqual(feed.stats_24h()["BTC"]["variation_24h_pct"] is not None, True)

    def test_every_exchange_down_raises_with_reasons(self):
        feed = MultiExchangeFeed(["BTC"], get=failing_get)
        with self.assertRaises(FeedError) as ctx:
            feed.refresh()
        self.assertIn("Gate", str(ctx.exception))
        self.assertTrue(all(st != "ok" for st in feed.status.values()))


if __name__ == "__main__":
    unittest.main()


class ApiConfigTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "apis.json"

    def test_custom_api_is_saved_tested_and_used(self):
        from crypto_arena.live.config import ApiConfig
        from crypto_arena.live.exchanges import extract
        PAYLOADS["mexc.com/api/v3/ticker/price?symbol=BTCUSDT"] = {"symbol": "BTCUSDT", "price": "60015"}
        self.addCleanup(PAYLOADS.pop, "mexc.com/api/v3/ticker/price?symbol=BTCUSDT")
        cfg = ApiConfig(self.path)
        cfg.update({"exchanges": {"KuCoin": False}, "anthropic_api_key": "sk-ant-test-1234",
                    "custom": [{"name": "MEXC", "url": "https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"}]})
        cfg = ApiConfig(self.path)  # relue depuis le disque
        self.assertFalse(cfg.enabled["KuCoin"])
        self.assertEqual(cfg.public()["anthropic"]["hint"], "…1234")
        self.assertNotIn("sk-ant-test-1234", str(cfg.public()))
        fake_claude = type("C", (), {"models": type("M", (), {"retrieve": lambda self, m: type("I", (), {"display_name": "Claude"})()})()})()
        result = cfg.test(get=fake_get, symbols=("BTC",), anthropic_client=fake_claude)
        by_name = {r["name"]: r for r in result["sources"]}
        self.assertTrue(by_name["MEXC"]["ok"])
        self.assertEqual(by_name["MEXC"]["prices"]["BTC"], 60015.0)
        self.assertNotIn("KuCoin", by_name)
        self.assertTrue(result["anthropic"]["ok"])
        names = [e.name for e in cfg.exchanges(only=["MEXC", "Gate"], get=fake_get)]
        self.assertEqual(names, ["Gate", "MEXC"])
        self.assertEqual(extract({"result": {"XXBTZUSD": {"c": ["1.5", "2"]}}}, "result.*.c.0"), "1.5")

    def test_invalid_custom_api_is_refused(self):
        from crypto_arena.live.config import ApiConfig
        cfg = ApiConfig(self.path)
        with self.assertRaises(ValueError):
            cfg.update({"custom": [{"name": "X", "url": "https://exemple.com/prix"}]})  # pas de {symbol}
        with self.assertRaises(ValueError):
            cfg.update({"custom": [{"name": "Gate", "url": "https://x.com/{symbol}"}]})  # nom déjà pris


class SlowNetworkTest(unittest.TestCase):
    def test_unreachable_exchanges_fail_fast(self):
        import time
        calls = []

        def hanging_get(url, timeout=6.0, headers=None):
            calls.append(url)
            time.sleep(0.3)
            raise OSError("timed out")

        feed = MultiExchangeFeed(get=hanging_get, deadline=2.0)
        t0 = time.monotonic()
        with self.assertRaises(FeedError):
            feed.refresh()
        self.assertLess(time.monotonic() - t0, 1.5)
        kraken_calls = [u for u in calls if "kraken" in u]
        self.assertEqual(len(kraken_calls), 1)  # pas une attente par actif

    def test_too_slow_exchange_is_marked_and_others_still_count(self):
        import time

        def get(url, timeout=6.0, headers=None):
            if "kraken" in url:
                time.sleep(1.0)
            return fake_get(url)

        feed = MultiExchangeFeed(["BTC"], get=get, deadline=0.3)
        prices = feed.refresh()
        self.assertIn("BTC", prices)
        self.assertIn("pas de réponse", feed.status["Kraken"])
