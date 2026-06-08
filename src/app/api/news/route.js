import { NextResponse } from 'next/server';
import { hasFinnhubKey, fetchCompanyNews, getMockNews } from '@/lib/finnhub';
import { calculateSentimentScore } from '@/lib/algorithms';

function getSentimentLabel(score) {
  if (score > 0.15) return 'positive';
  if (score < -0.15) return 'negative';
  return 'neutral';
}

function analyzeHeadlineSentiment(headline) {
  const positiveKeywords = [
    'surge', 'soar', 'jump', 'gain', 'rise', 'bull', 'rally', 'beat', 'record',
    'growth', 'profit', 'strong', 'upgrade', 'buy', 'outperform', 'exceed',
    'boost', 'positive', 'opportunity', 'upside', 'breakout', 'momentum',
  ];
  const negativeKeywords = [
    'drop', 'fall', 'plunge', 'crash', 'loss', 'bear', 'sell', 'decline',
    'weak', 'miss', 'downgrade', 'underperform', 'risk', 'warning', 'concern',
    'cut', 'layoff', 'recession', 'debt', 'lawsuit', 'investigation', 'fraud',
  ];
  const text = headline.toLowerCase();
  let score = 0;
  for (const kw of positiveKeywords) {
    if (text.includes(kw)) score += 1;
  }
  for (const kw of negativeKeywords) {
    if (text.includes(kw)) score -= 1;
  }
  return getSentimentLabel(Math.max(-1, Math.min(1, score)));
}

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const symbolsParam = searchParams.get('symbols') || '';
  const symbols = symbolsParam.split(',').filter(Boolean);

  if (!symbols.length) {
    return NextResponse.json({ error: 'No symbols provided' }, { status: 400 });
  }

  if (!hasFinnhubKey()) {
    return NextResponse.json(getMockNews(symbols));
  }

  try {
    const now = new Date();
    const toDate = now.toISOString().split('T')[0];
    const fromDate = new Date(now.getTime() - 7 * 86400000).toISOString().split('T')[0];

    const allNews = [];
    for (const symbol of symbols) {
      try {
        const items = await fetchCompanyNews(symbol, fromDate, toDate);
        const tagged = (items || []).slice(0, 5).map((item) => ({
          ...item,
          symbol,
          sentiment: analyzeHeadlineSentiment(item.headline || ''),
        }));
        allNews.push(...tagged);
      } catch {
        // skip symbol
      }
    }

    allNews.sort((a, b) => b.datetime - a.datetime);
    return NextResponse.json(allNews.slice(0, 20));
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
