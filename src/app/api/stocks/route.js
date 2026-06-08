import { NextResponse } from 'next/server';
import { hasFinnhubKey, fetchQuote, fetchCandles, getMockStocks } from '@/lib/finnhub';

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

  try {
    const now = Math.floor(Date.now() / 1000);
    const sevenDaysAgo = now - 7 * 86400;

    const results = await Promise.all(
      symbols.map(async (symbol) => {
        try {
          const [quote, candles] = await Promise.all([
            fetchQuote(symbol),
            fetchCandles(symbol, sevenDaysAgo, now),
          ]);
          const sparkline = candles.s === 'ok' ? candles.c : [];
          return {
            symbol,
            name: symbol,
            price: quote.c,
            change: parseFloat((quote.c - quote.pc).toFixed(2)),
            changePct: parseFloat((((quote.c - quote.pc) / quote.pc) * 100).toFixed(2)),
            volume: quote.v || 0,
            high52: quote.h || 0,
            low52: quote.l || 0,
            sparkline,
          };
        } catch {
          return null;
        }
      })
    );

    return NextResponse.json(results.filter(Boolean));
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
