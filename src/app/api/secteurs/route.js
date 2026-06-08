import { NextResponse } from 'next/server';
import { hasFinnhubKey, fetchQuote } from '@/lib/finnhub';

const SECTOR_DATA = {
  energie: [
    { ticker: 'XOM', entreprise: 'Exxon Mobil', pe: 13.4, analyste: 'Achat', price: 114.6, change: 1.15, high52: 123.75, low52: 95.77 },
    { ticker: 'CVX', entreprise: 'Chevron Corp.', pe: 14.1, analyste: 'Achat', price: 157.2, change: 0.82, high52: 172.0, low52: 138.9 },
    { ticker: 'COP', entreprise: 'ConocoPhillips', pe: 12.8, analyste: 'Fort Achat', price: 109.3, change: 1.45, high52: 129.4, low52: 97.6 },
    { ticker: 'SLB', entreprise: 'SLB (Schlumberger)', pe: 15.2, analyste: 'Fort Achat', price: 43.8, change: -0.68, high52: 59.8, low52: 40.1 },
    { ticker: 'OXY', entreprise: 'Occidental Petroleum', pe: 11.9, analyste: 'Achat', price: 53.4, change: 2.1, high52: 71.2, low52: 48.3 },
    { ticker: 'BP', entreprise: 'BP p.l.c.', pe: 9.7, analyste: 'Conserver', price: 34.2, change: -0.45, high52: 41.8, low52: 31.5 },
    { ticker: 'SHEL', entreprise: 'Shell plc', pe: 10.3, analyste: 'Achat', price: 65.8, change: 0.92, high52: 73.4, low52: 58.9 },
  ],
  tech: [
    { ticker: 'AAPL', entreprise: 'Apple Inc.', pe: 28.4, analyste: 'Fort Achat', price: 189.3, change: 0.66, high52: 199.62, low52: 164.08 },
    { ticker: 'NVDA', entreprise: 'NVIDIA Corp.', pe: 65.2, analyste: 'Fort Achat', price: 875.4, change: 2.76, high52: 974.0, low52: 410.17 },
    { ticker: 'MSFT', entreprise: 'Microsoft Corp.', pe: 34.8, analyste: 'Fort Achat', price: 415.2, change: -0.55, high52: 430.82, low52: 309.45 },
    { ticker: 'GOOGL', entreprise: 'Alphabet Inc.', pe: 24.1, analyste: 'Fort Achat', price: 176.5, change: 1.79, high52: 193.31, low52: 115.83 },
    { ticker: 'META', entreprise: 'Meta Platforms', pe: 23.7, analyste: 'Fort Achat', price: 508.9, change: 1.68, high52: 531.49, low52: 279.4 },
    { ticker: 'AMD', entreprise: 'Advanced Micro Devices', pe: 42.3, analyste: 'Achat', price: 168.4, change: -1.23, high52: 227.3, low52: 147.4 },
    { ticker: 'INTC', entreprise: 'Intel Corp.', pe: 18.6, analyste: 'Conserver', price: 21.3, change: -2.1, high52: 51.3, low52: 18.5 },
  ],
  sante: [
    { ticker: 'JNJ', entreprise: 'Johnson & Johnson', pe: 16.2, analyste: 'Achat', price: 152.3, change: -0.52, high52: 175.97, low52: 143.13 },
    { ticker: 'PFE', entreprise: 'Pfizer Inc.', pe: 11.8, analyste: 'Conserver', price: 27.4, change: -1.08, high52: 32.8, low52: 24.5 },
    { ticker: 'MRK', entreprise: 'Merck & Co.', pe: 14.3, analyste: 'Fort Achat', price: 101.2, change: 0.74, high52: 134.6, low52: 97.4 },
    { ticker: 'ABBV', entreprise: 'AbbVie Inc.', pe: 15.7, analyste: 'Fort Achat', price: 178.4, change: 1.22, high52: 199.5, low52: 148.7 },
    { ticker: 'UNH', entreprise: 'UnitedHealth Group', pe: 18.9, analyste: 'Fort Achat', price: 489.3, change: 0.41, high52: 600.2, low52: 432.1 },
    { ticker: 'LLY', entreprise: 'Eli Lilly', pe: 51.4, analyste: 'Fort Achat', price: 763.8, change: 1.87, high52: 972.5, low52: 562.3 },
    { ticker: 'BMY', entreprise: 'Bristol-Myers Squibb', pe: 8.4, analyste: 'Conserver', price: 49.8, change: -0.62, high52: 64.7, low52: 42.3 },
  ],
  finance: [
    { ticker: 'JPM', entreprise: 'JPMorgan Chase', pe: 11.4, analyste: 'Fort Achat', price: 198.7, change: 0.45, high52: 220.82, low52: 135.19 },
    { ticker: 'BAC', entreprise: 'Bank of America', pe: 12.1, analyste: 'Achat', price: 34.8, change: 0.87, high52: 39.2, low52: 24.6 },
    { ticker: 'GS', entreprise: 'Goldman Sachs', pe: 13.8, analyste: 'Fort Achat', price: 487.3, change: 1.34, high52: 531.0, low52: 323.8 },
    { ticker: 'MS', entreprise: 'Morgan Stanley', pe: 14.2, analyste: 'Achat', price: 98.4, change: 0.56, high52: 109.6, low52: 71.3 },
    { ticker: 'V', entreprise: 'Visa Inc.', pe: 29.3, analyste: 'Fort Achat', price: 278.9, change: 1.16, high52: 290.96, low52: 222.93 },
    { ticker: 'MA', entreprise: 'Mastercard Inc.', pe: 31.7, analyste: 'Fort Achat', price: 458.2, change: 0.93, high52: 492.8, low52: 368.5 },
    { ticker: 'BLK', entreprise: 'BlackRock Inc.', pe: 21.4, analyste: 'Achat', price: 834.6, change: 0.68, high52: 1028.7, low52: 632.5 },
  ],
  industrie: [
    { ticker: 'CAT', entreprise: 'Caterpillar Inc.', pe: 16.8, analyste: 'Achat', price: 348.2, change: 0.82, high52: 418.5, low52: 263.4 },
    { ticker: 'DE', entreprise: 'Deere & Company', pe: 14.2, analyste: 'Achat', price: 392.4, change: 1.14, high52: 469.8, low52: 345.2 },
    { ticker: 'BA', entreprise: 'Boeing Co.', pe: 0, analyste: 'Conserver', price: 167.8, change: -1.42, high52: 267.5, low52: 137.9 },
    { ticker: 'GE', entreprise: 'GE Aerospace', pe: 34.6, analyste: 'Fort Achat', price: 168.4, change: 2.31, high52: 194.3, low52: 87.6 },
    { ticker: 'HON', entreprise: 'Honeywell Intl.', pe: 21.3, analyste: 'Achat', price: 205.7, change: 0.37, high52: 229.7, low52: 183.4 },
    { ticker: 'MMM', entreprise: '3M Company', pe: 15.1, analyste: 'Conserver', price: 124.3, change: -0.48, high52: 148.9, low52: 85.4 },
    { ticker: 'UPS', entreprise: 'United Parcel Service', pe: 18.7, analyste: 'Conserver', price: 131.8, change: -0.73, high52: 168.9, low52: 119.3 },
  ],
};

function computeScore(company) {
  const range = company.high52 - company.low52;
  const positionInRange = range > 0 ? ((company.price - company.low52) / range) * 100 : 50;
  const positionScore = Math.max(0, 100 - positionInRange);

  const peScore = company.pe === 0 ? 20 : Math.max(0, Math.min(40, (40 - company.pe) * 1.2 + 20));

  const analysteScores = { 'Fort Achat': 30, 'Achat': 20, 'Conserver': 5, 'Vente': -10 };
  const analysteScore = analysteScores[company.analyste] ?? 5;

  const momentumScore = company.change > 1.5 ? 15 : company.change > 0 ? 8 : company.change > -1 ? 4 : 0;

  const raw = positionScore * 0.35 + peScore * 0.3 + analysteScore + momentumScore;
  return Math.round(Math.max(0, Math.min(100, raw)));
}

function scoreLabel(score) {
  if (score > 75) return 'FORTE OPPORTUNITÉ';
  if (score >= 50) return 'OPPORTUNITÉ';
  if (score >= 30) return 'NEUTRE';
  return 'RISQUÉ';
}

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const sector = searchParams.get('sector') || '';

  const companies = SECTOR_DATA[sector];
  if (!companies) {
    return NextResponse.json({ error: 'Invalid sector' }, { status: 400 });
  }

  let results;

  if (hasFinnhubKey()) {
    results = await Promise.all(
      companies.map(async (c) => {
        try {
          const quote = await fetchQuote(c.ticker);
          const price = quote.c || c.price;
          const change = quote.c && quote.pc ? parseFloat((((quote.c - quote.pc) / quote.pc) * 100).toFixed(2)) : c.change;
          const updated = { ...c, price, change };
          const score = computeScore(updated);
          return { ...updated, score, label: scoreLabel(score) };
        } catch {
          const score = computeScore(c);
          return { ...c, score, label: scoreLabel(score) };
        }
      })
    );
  } else {
    results = companies.map((c) => {
      const score = computeScore(c);
      return { ...c, score, label: scoreLabel(score) };
    });
  }

  results.sort((a, b) => b.score - a.score);
  return NextResponse.json(results);
}
