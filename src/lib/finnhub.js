const FINNHUB_API_KEY = process.env.FINNHUB_API_KEY;
const BASE_URL = 'https://finnhub.io/api/v1';

export function hasFinnhubKey() {
  return !!FINNHUB_API_KEY && FINNHUB_API_KEY !== 'your_key_here';
}

export async function fetchQuote(symbol) {
  const res = await fetch(`${BASE_URL}/quote?symbol=${symbol}&token=${FINNHUB_API_KEY}`);
  if (!res.ok) throw new Error(`Finnhub quote error for ${symbol}`);
  return res.json();
}

export async function fetchCandles(symbol, from, to) {
  const res = await fetch(
    `${BASE_URL}/stock/candle?symbol=${symbol}&resolution=D&from=${from}&to=${to}&token=${FINNHUB_API_KEY}`
  );
  if (!res.ok) throw new Error(`Finnhub candles error for ${symbol}`);
  return res.json();
}

export async function fetchCompanyNews(symbol, from, to) {
  const res = await fetch(
    `${BASE_URL}/company-news?symbol=${symbol}&from=${from}&to=${to}&token=${FINNHUB_API_KEY}`
  );
  if (!res.ok) throw new Error(`Finnhub news error for ${symbol}`);
  return res.json();
}

export async function fetchProfile(symbol) {
  const res = await fetch(`${BASE_URL}/stock/profile2?symbol=${symbol}&token=${FINNHUB_API_KEY}`);
  if (!res.ok) throw new Error(`Finnhub profile error for ${symbol}`);
  return res.json();
}

const MOCK_STOCKS = {
  AAPL: { name: 'Apple Inc.', price: 189.3, change: 1.24, changePct: 0.66, volume: 52340000, high52: 199.62, low52: 164.08 },
  NVDA: { name: 'NVIDIA Corp.', price: 875.4, change: 23.5, changePct: 2.76, volume: 41230000, high52: 974.0, low52: 410.17 },
  MSFT: { name: 'Microsoft Corp.', price: 415.2, change: -2.3, changePct: -0.55, volume: 18760000, high52: 430.82, low52: 309.45 },
  GOOGL: { name: 'Alphabet Inc.', price: 176.5, change: 3.1, changePct: 1.79, volume: 22450000, high52: 193.31, low52: 115.83 },
  META: { name: 'Meta Platforms', price: 508.9, change: 8.4, changePct: 1.68, volume: 15680000, high52: 531.49, low52: 279.4 },
  TSLA: { name: 'Tesla Inc.', price: 172.8, change: -4.6, changePct: -2.59, volume: 89340000, high52: 278.98, low52: 138.8 },
  AMZN: { name: 'Amazon.com Inc.', price: 188.4, change: 2.7, changePct: 1.45, volume: 35670000, high52: 201.2, low52: 118.35 },
  JPM: { name: 'JPMorgan Chase', price: 198.7, change: 0.9, changePct: 0.45, volume: 9870000, high52: 220.82, low52: 135.19 },
  JNJ: { name: 'Johnson & Johnson', price: 152.3, change: -0.8, changePct: -0.52, volume: 7230000, high52: 175.97, low52: 143.13 },
  XOM: { name: 'Exxon Mobil Corp.', price: 114.6, change: 1.3, changePct: 1.15, volume: 14560000, high52: 123.75, low52: 95.77 },
  WMT: { name: 'Walmart Inc.', price: 67.8, change: 0.4, changePct: 0.59, volume: 11230000, high52: 74.01, low52: 49.85 },
  'BRK.B': { name: 'Berkshire Hathaway', price: 388.5, change: 1.2, changePct: 0.31, volume: 4120000, high52: 394.98, low52: 320.07 },
  PG: { name: 'Procter & Gamble', price: 162.4, change: -0.6, changePct: -0.37, volume: 6540000, high52: 173.69, low52: 138.78 },
  V: { name: 'Visa Inc.', price: 278.9, change: 3.2, changePct: 1.16, volume: 8970000, high52: 290.96, low52: 222.93 },
};

function generateSparkline(basePrice, days = 7) {
  const prices = [];
  let p = basePrice * (0.92 + Math.random() * 0.08);
  for (let i = 0; i < days; i++) {
    p = p * (1 + (Math.random() - 0.48) * 0.025);
    prices.push(parseFloat(p.toFixed(2)));
  }
  prices.push(basePrice);
  return prices;
}

function generateCandles(basePrice, days = 180) {
  const closes = [];
  const highs = [];
  const lows = [];
  const opens = [];
  const timestamps = [];
  const volumes = [];
  let p = basePrice * (0.75 + Math.random() * 0.25);
  const now = Math.floor(Date.now() / 1000);
  for (let i = days; i >= 0; i--) {
    const open = p;
    const change = p * (Math.random() - 0.48) * 0.03;
    const close = p + change;
    const high = Math.max(open, close) * (1 + Math.random() * 0.01);
    const low = Math.min(open, close) * (1 - Math.random() * 0.01);
    opens.push(parseFloat(open.toFixed(2)));
    closes.push(parseFloat(close.toFixed(2)));
    highs.push(parseFloat(high.toFixed(2)));
    lows.push(parseFloat(low.toFixed(2)));
    timestamps.push(now - i * 86400);
    volumes.push(Math.floor(5000000 + Math.random() * 50000000));
    p = close;
  }
  return { o: opens, c: closes, h: highs, l: lows, t: timestamps, v: volumes, s: 'ok' };
}

const MOCK_NEWS_TEMPLATES = [
  { headline: 'Q4 earnings beat analyst expectations with record revenue growth', sentiment: 'positive' },
  { headline: 'Stock surges after strong quarterly results and raised guidance', sentiment: 'positive' },
  { headline: 'Company announces major partnership to boost market expansion', sentiment: 'positive' },
  { headline: 'Analysts upgrade rating to Buy following robust performance', sentiment: 'positive' },
  { headline: 'Revenue growth momentum continues to outperform sector peers', sentiment: 'positive' },
  { headline: 'Shares fall on concerns over slowing demand and margin pressure', sentiment: 'negative' },
  { headline: 'Company misses earnings forecast, warns of challenging outlook', sentiment: 'negative' },
  { headline: 'Investigation launched into accounting practices, stock drops', sentiment: 'negative' },
  { headline: 'Layoffs announced as company restructures amid declining sales', sentiment: 'negative' },
  { headline: 'Management shake-up raises concerns about strategic direction', sentiment: 'neutral' },
  { headline: 'Board approves new share buyback program worth $5 billion', sentiment: 'positive' },
  { headline: 'Market volatility creates uncertainty for near-term outlook', sentiment: 'neutral' },
];

const SOURCES = [
  { name: 'Reuters', url: 'https://www.reuters.com/markets/' },
  { name: 'Bloomberg', url: 'https://www.bloomberg.com/markets' },
  { name: 'CNBC', url: 'https://www.cnbc.com/markets/' },
  { name: 'MarketWatch', url: 'https://www.marketwatch.com/' },
  { name: 'The Wall Street Journal', url: 'https://www.wsj.com/market-data' },
  { name: 'Financial Times', url: 'https://www.ft.com/markets' },
  { name: "Barron's", url: 'https://www.barrons.com/market-data' },
];

export function getMockStocks(symbols) {
  return symbols.map((symbol) => {
    const data = MOCK_STOCKS[symbol] || {
      name: symbol,
      price: 100 + Math.random() * 400,
      change: (Math.random() - 0.5) * 10,
      changePct: (Math.random() - 0.5) * 5,
      volume: Math.floor(5000000 + Math.random() * 50000000),
      high52: 0,
      low52: 0,
    };
    return {
      symbol,
      name: data.name,
      price: data.price,
      change: parseFloat(data.change.toFixed(2)),
      changePct: parseFloat(data.changePct.toFixed(2)),
      volume: data.volume,
      high52: data.high52,
      low52: data.low52,
      sparkline: generateSparkline(data.price),
    };
  });
}

export function getMockNews(symbols) {
  const news = [];
  const now = Date.now();
  symbols.forEach((symbol) => {
    const count = Math.floor(2 + Math.random() * 3);
    for (let i = 0; i < count; i++) {
      const template = MOCK_NEWS_TEMPLATES[Math.floor(Math.random() * MOCK_NEWS_TEMPLATES.length)];
      const stockData = MOCK_STOCKS[symbol];
      const src = SOURCES[Math.floor(Math.random() * SOURCES.length)];
      news.push({
        id: `${symbol}-${i}-${now}`,
        symbol,
        headline: `${stockData ? stockData.name : symbol}: ${template.headline}`,
        source: src.name,
        datetime: Math.floor((now - Math.random() * 7 * 86400000) / 1000),
        summary: `Investors and analysts are closely watching ${symbol} as the company navigates market conditions. This development could have significant implications for the stock's near-term performance and long-term valuation.`,
        url: null,
        sentiment: template.sentiment,
      });
    }
  });
  news.sort((a, b) => b.datetime - a.datetime);
  return news.slice(0, 20);
}

export function getMockCandles(symbol) {
  const data = MOCK_STOCKS[symbol];
  const basePrice = data ? data.price : 150;
  return generateCandles(basePrice);
}

export function getMockAnalysis(symbol) {
  const data = MOCK_STOCKS[symbol];
  return {
    symbol,
    name: data ? data.name : symbol,
    price: data ? data.price : 150,
    high52: data ? data.high52 : 200,
    low52: data ? data.low52 : 100,
  };
}
