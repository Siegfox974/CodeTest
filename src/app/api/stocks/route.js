import { NextResponse } from 'next/server';
import { hasFinnhubKey, fetchQuote, fetchCandles, getMockStocks } from '@/lib/finnhub';

async function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const symbolsParam = searchParams.get('symbols') || '';
  const symbols = symbolsParam.split(',').filter(Boolean);

  if (!symbols.length) {
    return NextResponse.json({ error: 'No symbols provided' }, { status: 400 });
  }

  if (!hasFinnhubKey()) {
    return NextResponse.json(getMockStocks(symbols));
  }

  const now = Math.floor(Date.now() / 1000);
  const sevenDaysAgo = now - 7 * 86400;
  const results = [];

  for (let i = 0; i < symbols.length; i++) {
    const symbol = symbols[i];
    try {
      const quote = await fetchQuote(symbol);
      if (!quote.c) {
        results.push(null);
        continue;
      }
      let sparkline = [];
      try {
        const candles = await fetchCandles(symbol, sevenDaysAgo, now);
        if (candles.s === 'ok') sparkline = candles.c;
      } catch {
        // sparkline non critique, on continue sans
      }
      results.push({
        symbol,
        name: symbol,
        price: quote.c,
        change: parseFloat((quote.c - quote.pc).toFixed(2)),
        changePct: parseFloat((((quote.c - quote.pc) / quote.pc) * 100).toFixed(2)),
        volume: quote.v || 0,
        high52: quote.h || 0,
        low52: quote.l || 0,
        sparkline,
      });
    } catch {
      results.push(null);
    }
    if (i < symbols.length - 1) await delay(120);
  }

  return NextResponse.json(results.filter(Boolean));
}
