export function calculateEMA(prices, period) {
  if (prices.length < period) return [];
  const k = 2 / (period + 1);
  const emaArray = [];
  let ema = prices.slice(0, period).reduce((a, b) => a + b, 0) / period;
  emaArray.push(ema);
  for (let i = period; i < prices.length; i++) {
    ema = prices[i] * k + ema * (1 - k);
    emaArray.push(ema);
  }
  return emaArray;
}

export function calculateMA(prices, period) {
  if (prices.length < period) return null;
  const slice = prices.slice(-period);
  return slice.reduce((a, b) => a + b, 0) / period;
}

export function calculateRSI(prices, period = 14) {
  if (prices.length < period + 1) return null;
  let gains = 0;
  let losses = 0;
  for (let i = 1; i <= period; i++) {
    const diff = prices[i] - prices[i - 1];
    if (diff >= 0) gains += diff;
    else losses += Math.abs(diff);
  }
  let avgGain = gains / period;
  let avgLoss = losses / period;
  for (let i = period + 1; i < prices.length; i++) {
    const diff = prices[i] - prices[i - 1];
    const gain = diff >= 0 ? diff : 0;
    const loss = diff < 0 ? Math.abs(diff) : 0;
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
  }
  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return 100 - 100 / (1 + rs);
}

export function calculateMACD(prices) {
  if (prices.length < 26) return null;
  const ema12 = calculateEMA(prices, 12);
  const ema26 = calculateEMA(prices, 26);
  const offset = ema12.length - ema26.length;
  const macdLine = ema26.map((v, i) => ema12[i + offset] - v);
  const signalLine = calculateEMA(macdLine, 9);
  const macdOffsetForSignal = macdLine.length - signalLine.length;
  const lastMACD = macdLine[macdLine.length - 1];
  const lastSignal = signalLine[signalLine.length - 1];
  const histogram = lastMACD - lastSignal;
  return {
    macd: lastMACD,
    signal: lastSignal,
    histogram,
    bullish: lastMACD > lastSignal,
  };
}

export function calculateSentimentScore(newsArray) {
  if (!newsArray || newsArray.length === 0) return 0;
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
  let totalScore = 0;
  for (const item of newsArray) {
    const text = (item.headline || item.title || '').toLowerCase();
    let score = 0;
    for (const kw of positiveKeywords) {
      if (text.includes(kw)) score += 1;
    }
    for (const kw of negativeKeywords) {
      if (text.includes(kw)) score -= 1;
    }
    totalScore += Math.max(-1, Math.min(1, score));
  }
  return totalScore / newsArray.length;
}

export function calculateOverallScore(rsi, macd, ma50, ma200, sentiment, currentPrice) {
  let score = 50;

  if (rsi !== null) {
    if (rsi < 30) score += 15;
    else if (rsi < 40) score += 8;
    else if (rsi > 70) score -= 15;
    else if (rsi > 60) score -= 8;
  }

  if (macd !== null) {
    if (macd.bullish) score += 10;
    else score -= 10;
    if (macd.histogram > 0) score += 5;
    else score -= 5;
  }

  if (ma50 !== null && ma200 !== null && currentPrice) {
    if (ma50 > ma200) score += 10;
    else score -= 10;
    if (currentPrice > ma50) score += 5;
    else score -= 5;
  }

  if (sentiment !== null) {
    score += sentiment * 15;
  }

  return Math.round(Math.max(0, Math.min(100, score)));
}

export function getRecommendation(score) {
  if (score >= 75) return { label: 'FORT SIGNAL D\'ACHAT', color: 'emerald' };
  if (score >= 60) return { label: 'SIGNAL D\'ACHAT', color: 'green' };
  if (score >= 40) return { label: 'NEUTRE', color: 'yellow' };
  if (score >= 25) return { label: 'SIGNAL DE VENTE', color: 'orange' };
  return { label: 'FORT SIGNAL DE VENTE', color: 'red' };
}
