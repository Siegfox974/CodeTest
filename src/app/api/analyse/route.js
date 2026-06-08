import { NextResponse } from 'next/server';
import {
  hasFinnhubKey,
  fetchCandles,
  fetchCompanyNews,
  getMockCandles,
  getMockNews,
  getMockAnalysis,
} from '@/lib/finnhub';
import {
  calculateRSI,
  calculateMACD,
  calculateMA,
  calculateSentimentScore,
  calculateOverallScore,
  getRecommendation,
} from '@/lib/algorithms';

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const symbol = searchParams.get('symbol');

  if (!symbol) {
    return NextResponse.json({ error: 'No symbol provided' }, { status: 400 });
  }

  try {
    let candles, newsItems, baseInfo;

    if (!hasFinnhubKey()) {
      candles = getMockCandles(symbol);
      newsItems = getMockNews([symbol]);
      baseInfo = getMockAnalysis(symbol);
    } else {
      const now = Math.floor(Date.now() / 1000);
      const sixMonthsAgo = now - 180 * 86400;
      const toDate = new Date().toISOString().split('T')[0];
      const fromDate = new Date(Date.now() - 7 * 86400000).toISOString().split('T')[0];

      [candles, newsItems] = await Promise.all([
        fetchCandles(symbol, sixMonthsAgo, now),
        fetchCompanyNews(symbol, fromDate, toDate),
      ]);

      const closes = candles.s === 'ok' ? candles.c : [];
      const currentPrice = closes[closes.length - 1] || 0;
      const highs = candles.h || [];
      const lows = candles.l || [];
      const high52 = highs.length ? Math.max(...highs) : 0;
      const low52 = lows.length ? Math.min(...lows) : 0;
      baseInfo = { symbol, name: symbol, price: currentPrice, high52, low52 };
    }

    const closes = candles.s === 'ok' ? candles.c : [];
    const currentPrice = baseInfo.price;

    const rsi = calculateRSI(closes, 14);
    const macd = calculateMACD(closes);
    const ma50 = calculateMA(closes, 50);
    const ma200 = calculateMA(closes, 200);
    const sentimentScore = calculateSentimentScore(newsItems);
    const overallScore = calculateOverallScore(rsi, macd, ma50, ma200, sentimentScore, currentPrice);
    const recommendation = getRecommendation(overallScore);

    const goldenCross = ma50 !== null && ma200 !== null && ma50 > ma200;
    const deathCross = ma50 !== null && ma200 !== null && ma50 < ma200;

    return NextResponse.json({
      symbol,
      name: baseInfo.name,
      price: currentPrice,
      high52: baseInfo.high52,
      low52: baseInfo.low52,
      rsi: rsi !== null ? parseFloat(rsi.toFixed(2)) : null,
      macd: macd
        ? {
            macd: parseFloat(macd.macd.toFixed(4)),
            signal: parseFloat(macd.signal.toFixed(4)),
            histogram: parseFloat(macd.histogram.toFixed(4)),
            bullish: macd.bullish,
          }
        : null,
      ma50: ma50 !== null ? parseFloat(ma50.toFixed(2)) : null,
      ma200: ma200 !== null ? parseFloat(ma200.toFixed(2)) : null,
      goldenCross,
      deathCross,
      sentimentScore: parseFloat(sentimentScore.toFixed(3)),
      overallScore,
      recommendation,
      closePrices: closes.slice(-30),
    });
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
