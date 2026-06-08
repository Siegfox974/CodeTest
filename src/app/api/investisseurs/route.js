import { NextResponse } from 'next/server';

const BUFFETT_HOLDINGS = [
  { entreprise: 'Apple Inc.', ticker: 'AAPL', secteur: 'Technologie', valeur: '174.3B', pct: 40.2, declaration: '2024-11-15', action: 'Maintien' },
  { entreprise: 'Bank of America', ticker: 'BAC', secteur: 'Finance', valeur: '43.2B', pct: 9.8, declaration: '2024-11-15', action: 'Vente' },
  { entreprise: 'American Express', ticker: 'AXP', secteur: 'Finance', valeur: '41.1B', pct: 9.3, declaration: '2024-11-15', action: 'Maintien' },
  { entreprise: 'Coca-Cola', ticker: 'KO', secteur: 'Consommation', valeur: '35.5B', pct: 8.1, declaration: '2024-11-15', action: 'Maintien' },
  { entreprise: 'Chevron', ticker: 'CVX', secteur: 'Énergie', valeur: '26.8B', pct: 6.1, declaration: '2024-11-15', action: 'Vente' },
  { entreprise: 'Occidental Petroleum', ticker: 'OXY', secteur: 'Énergie', valeur: '22.4B', pct: 5.1, declaration: '2024-11-15', action: 'Achat' },
  { entreprise: 'Kraft Heinz', ticker: 'KHC', secteur: 'Consommation', valeur: '11.2B', pct: 2.6, declaration: '2024-11-15', action: 'Maintien' },
  { entreprise: "Moody's Corp", ticker: 'MCO', secteur: 'Finance', valeur: '9.8B', pct: 2.2, declaration: '2024-11-15', action: 'Maintien' },
  { entreprise: 'DaVita Inc.', ticker: 'DVA', secteur: 'Santé', valeur: '6.1B', pct: 1.4, declaration: '2024-11-15', action: 'Achat' },
  { entreprise: 'Citigroup', ticker: 'C', secteur: 'Finance', valeur: '5.9B', pct: 1.3, declaration: '2024-11-15', action: 'Achat' },
];

const BURRY_HOLDINGS = [
  { entreprise: 'Alibaba Group', ticker: 'BABA', secteur: 'Technologie', valeur: '18.7M', pct: 15.1, declaration: '2024-11-14', action: 'Achat' },
  { entreprise: 'JD.com', ticker: 'JD', secteur: 'Consommation', valeur: '14.9M', pct: 12.0, declaration: '2024-11-14', action: 'Maintien' },
  { entreprise: 'Baidu Inc.', ticker: 'BIDU', secteur: 'Technologie', valeur: '12.4M', pct: 10.0, declaration: '2024-11-14', action: 'Achat' },
  { entreprise: 'PDD Holdings', ticker: 'PDD', secteur: 'Consommation', valeur: '9.9M', pct: 8.0, declaration: '2024-11-14', action: 'Achat' },
  { entreprise: 'HCA Healthcare', ticker: 'HCA', secteur: 'Santé', valeur: '8.7M', pct: 7.0, declaration: '2024-11-14', action: 'Achat' },
  { entreprise: 'MGM Resorts', ticker: 'MGM', secteur: 'Loisirs', valeur: '7.4M', pct: 6.0, declaration: '2024-11-14', action: 'Maintien' },
  { entreprise: 'Shift4 Payments', ticker: 'FOUR', secteur: 'Finance', valeur: '6.2M', pct: 5.0, declaration: '2024-11-14', action: 'Achat' },
  { entreprise: 'Molina Healthcare', ticker: 'MOH', secteur: 'Santé', valeur: '4.9M', pct: 4.0, declaration: '2024-11-14', action: 'Vente' },
  { entreprise: 'Civitas Resources', ticker: 'CIVI', secteur: 'Énergie', valeur: '3.7M', pct: 3.0, declaration: '2024-11-14', action: 'Achat' },
  { entreprise: 'Nexstar Media', ticker: 'NXST', secteur: 'Médias', valeur: '2.5M', pct: 2.0, declaration: '2024-11-14', action: 'Maintien' },
];

const WOOD_HOLDINGS = [
  { entreprise: 'Tesla Inc.', ticker: 'TSLA', secteur: 'Technologie', valeur: '2.1B', pct: 10.2, declaration: '2024-12-20', action: 'Achat' },
  { entreprise: 'Coinbase Global', ticker: 'COIN', secteur: 'Finance', valeur: '1.6B', pct: 7.9, declaration: '2024-12-20', action: 'Achat' },
  { entreprise: 'Roku Inc.', ticker: 'ROKU', secteur: 'Technologie', valeur: '1.2B', pct: 5.9, declaration: '2024-12-20', action: 'Maintien' },
  { entreprise: 'UiPath Inc.', ticker: 'PATH', secteur: 'Technologie', valeur: '1.0B', pct: 5.0, declaration: '2024-12-20', action: 'Achat' },
  { entreprise: 'CRISPR Therapeutics', ticker: 'CRSP', secteur: 'Santé', valeur: '0.8B', pct: 4.1, declaration: '2024-12-20', action: 'Maintien' },
  { entreprise: 'NVIDIA Corp.', ticker: 'NVDA', secteur: 'Technologie', valeur: '0.8B', pct: 4.0, declaration: '2024-12-20', action: 'Achat' },
  { entreprise: 'Palantir Technologies', ticker: 'PLTR', secteur: 'Technologie', valeur: '0.7B', pct: 3.5, declaration: '2024-12-20', action: 'Achat' },
  { entreprise: 'Block Inc.', ticker: 'SQ', secteur: 'Finance', valeur: '0.7B', pct: 3.3, declaration: '2024-12-20', action: 'Maintien' },
  { entreprise: 'Zoom Video', ticker: 'ZM', secteur: 'Technologie', valeur: '0.6B', pct: 2.9, declaration: '2024-12-20', action: 'Vente' },
  { entreprise: 'Shopify Inc.', ticker: 'SHOP', secteur: 'Technologie', valeur: '0.6B', pct: 2.8, declaration: '2024-12-20', action: 'Achat' },
];

const PELOSI_MOCK = [
  { entreprise: 'NVIDIA Corp.', ticker: 'NVDA', secteur: 'Technologie', valeur: '$5M-$25M', pct: 22.0, declaration: '2024-12-15', action: 'Achat' },
  { entreprise: 'Apple Inc.', ticker: 'AAPL', secteur: 'Technologie', valeur: '$1M-$5M', pct: 12.0, declaration: '2024-11-20', action: 'Achat' },
  { entreprise: 'Microsoft Corp.', ticker: 'MSFT', secteur: 'Technologie', valeur: '$1M-$5M', pct: 11.0, declaration: '2024-11-20', action: 'Achat' },
  { entreprise: 'Amazon.com Inc.', ticker: 'AMZN', secteur: 'Technologie', valeur: '$1M-$5M', pct: 10.0, declaration: '2024-10-18', action: 'Achat' },
  { entreprise: 'Alphabet Inc.', ticker: 'GOOGL', secteur: 'Technologie', valeur: '$500K-$1M', pct: 8.0, declaration: '2024-09-10', action: 'Achat' },
  { entreprise: 'Visa Inc.', ticker: 'V', secteur: 'Finance', valeur: '$500K-$1M', pct: 7.0, declaration: '2024-08-15', action: 'Maintien' },
  { entreprise: 'Palo Alto Networks', ticker: 'PANW', secteur: 'Technologie', valeur: '$250K-$500K', pct: 5.0, declaration: '2024-06-14', action: 'Achat' },
];

const GREENE_MOCK = [
  { entreprise: 'Lockheed Martin', ticker: 'LMT', secteur: 'Défense', valeur: '$50K-$100K', pct: 18.0, declaration: '2024-11-08', action: 'Achat' },
  { entreprise: 'Exxon Mobil', ticker: 'XOM', secteur: 'Énergie', valeur: '$50K-$100K', pct: 15.0, declaration: '2024-10-22', action: 'Achat' },
  { entreprise: 'Raytheon Technologies', ticker: 'RTX', secteur: 'Défense', valeur: '$50K-$100K', pct: 14.0, declaration: '2024-10-01', action: 'Achat' },
  { entreprise: 'Chevron Corp.', ticker: 'CVX', secteur: 'Énergie', valeur: '$15K-$50K', pct: 11.0, declaration: '2024-09-15', action: 'Achat' },
  { entreprise: 'Apple Inc.', ticker: 'AAPL', secteur: 'Technologie', valeur: '$15K-$50K', pct: 10.0, declaration: '2024-08-30', action: 'Maintien' },
  { entreprise: 'Northrop Grumman', ticker: 'NOC', secteur: 'Défense', valeur: '$15K-$50K', pct: 9.0, declaration: '2024-08-12', action: 'Achat' },
  { entreprise: 'ConocoPhillips', ticker: 'COP', secteur: 'Énergie', valeur: '$15K-$50K', pct: 8.0, declaration: '2024-07-20', action: 'Achat' },
  { entreprise: 'Microsoft Corp.', ticker: 'MSFT', secteur: 'Technologie', valeur: '$15K-$50K', pct: 7.0, declaration: '2024-06-18', action: 'Achat' },
];

const SCHULTZ_MOCK = [
  { entreprise: 'Microsoft Corp.', ticker: 'MSFT', secteur: 'Technologie', valeur: '$100K-$250K', pct: 20.0, declaration: '2024-12-01', action: 'Achat' },
  { entreprise: 'Apple Inc.', ticker: 'AAPL', secteur: 'Technologie', valeur: '$100K-$250K', pct: 18.0, declaration: '2024-11-15', action: 'Maintien' },
  { entreprise: 'Alphabet Inc.', ticker: 'GOOGL', secteur: 'Technologie', valeur: '$50K-$100K', pct: 14.0, declaration: '2024-10-28', action: 'Achat' },
  { entreprise: 'Amazon.com Inc.', ticker: 'AMZN', secteur: 'Technologie', valeur: '$50K-$100K', pct: 12.0, declaration: '2024-09-20', action: 'Achat' },
  { entreprise: 'Visa Inc.', ticker: 'V', secteur: 'Finance', valeur: '$15K-$50K', pct: 9.0, declaration: '2024-08-14', action: 'Maintien' },
  { entreprise: 'JPMorgan Chase', ticker: 'JPM', secteur: 'Finance', valeur: '$15K-$50K', pct: 8.0, declaration: '2024-07-09', action: 'Achat' },
  { entreprise: 'Johnson & Johnson', ticker: 'JNJ', secteur: 'Santé', valeur: '$15K-$50K', pct: 7.0, declaration: '2024-06-25', action: 'Maintien' },
];

const GOTTHEIMER_MOCK = [
  { entreprise: 'NVIDIA Corp.', ticker: 'NVDA', secteur: 'Technologie', valeur: '$500K-$1M', pct: 25.0, declaration: '2024-12-10', action: 'Achat' },
  { entreprise: 'Apple Inc.', ticker: 'AAPL', secteur: 'Technologie', valeur: '$250K-$500K', pct: 18.0, declaration: '2024-11-22', action: 'Achat' },
  { entreprise: 'Meta Platforms', ticker: 'META', secteur: 'Technologie', valeur: '$100K-$250K', pct: 14.0, declaration: '2024-10-30', action: 'Achat' },
  { entreprise: 'Microsoft Corp.', ticker: 'MSFT', secteur: 'Technologie', valeur: '$100K-$250K', pct: 12.0, declaration: '2024-10-05', action: 'Maintien' },
  { entreprise: 'Goldman Sachs', ticker: 'GS', secteur: 'Finance', valeur: '$50K-$100K', pct: 10.0, declaration: '2024-09-18', action: 'Achat' },
  { entreprise: 'Palantir Technologies', ticker: 'PLTR', secteur: 'Technologie', valeur: '$50K-$100K', pct: 9.0, declaration: '2024-08-27', action: 'Achat' },
  { entreprise: 'Salesforce', ticker: 'CRM', secteur: 'Technologie', valeur: '$15K-$50K', pct: 7.0, declaration: '2024-07-15', action: 'Achat' },
];

const CRENSHAW_MOCK = [
  { entreprise: 'Exxon Mobil', ticker: 'XOM', secteur: 'Énergie', valeur: '$100K-$250K', pct: 22.0, declaration: '2024-11-18', action: 'Achat' },
  { entreprise: 'Lockheed Martin', ticker: 'LMT', secteur: 'Défense', valeur: '$100K-$250K', pct: 19.0, declaration: '2024-10-25', action: 'Achat' },
  { entreprise: 'ConocoPhillips', ticker: 'COP', secteur: 'Énergie', valeur: '$50K-$100K', pct: 15.0, declaration: '2024-10-02', action: 'Achat' },
  { entreprise: 'Halliburton', ticker: 'HAL', secteur: 'Énergie', valeur: '$50K-$100K', pct: 12.0, declaration: '2024-09-12', action: 'Achat' },
  { entreprise: 'Boeing Co.', ticker: 'BA', secteur: 'Défense', valeur: '$15K-$50K', pct: 10.0, declaration: '2024-08-20', action: 'Maintien' },
  { entreprise: 'Schlumberger', ticker: 'SLB', secteur: 'Énergie', valeur: '$15K-$50K', pct: 9.0, declaration: '2024-07-30', action: 'Achat' },
  { entreprise: 'Apple Inc.', ticker: 'AAPL', secteur: 'Technologie', valeur: '$15K-$50K', pct: 7.0, declaration: '2024-06-22', action: 'Achat' },
];

const AOC_MOCK = [
  { entreprise: 'Apple Inc.', ticker: 'AAPL', secteur: 'Technologie', valeur: '$1K-$15K', pct: 28.0, declaration: '2024-11-05', action: 'Maintien' },
  { entreprise: 'Amazon.com Inc.', ticker: 'AMZN', secteur: 'Technologie', valeur: '$1K-$15K', pct: 20.0, declaration: '2024-10-14', action: 'Maintien' },
  { entreprise: 'Microsoft Corp.', ticker: 'MSFT', secteur: 'Technologie', valeur: '$1K-$15K', pct: 16.0, declaration: '2024-09-28', action: 'Maintien' },
  { entreprise: 'Alphabet Inc.', ticker: 'GOOGL', secteur: 'Technologie', valeur: '$1K-$15K', pct: 12.0, declaration: '2024-09-05', action: 'Maintien' },
  { entreprise: 'Vanguard S&P 500 ETF', ticker: 'VOO', secteur: 'ETF', valeur: '$1K-$15K', pct: 14.0, declaration: '2024-08-18', action: 'Achat' },
  { entreprise: 'iShares MSCI Emerging', ticker: 'EEM', secteur: 'ETF', valeur: '$1K-$15K', pct: 10.0, declaration: '2024-07-22', action: 'Achat' },
];

const KHANNA_MOCK = [
  { entreprise: 'NVIDIA Corp.', ticker: 'NVDA', secteur: 'Technologie', valeur: '$250K-$500K', pct: 24.0, declaration: '2024-12-08', action: 'Achat' },
  { entreprise: 'Taiwan Semiconductor', ticker: 'TSM', secteur: 'Technologie', valeur: '$100K-$250K', pct: 18.0, declaration: '2024-11-19', action: 'Achat' },
  { entreprise: 'Apple Inc.', ticker: 'AAPL', secteur: 'Technologie', valeur: '$100K-$250K', pct: 15.0, declaration: '2024-10-30', action: 'Maintien' },
  { entreprise: 'AMD Inc.', ticker: 'AMD', secteur: 'Technologie', valeur: '$50K-$100K', pct: 13.0, declaration: '2024-10-08', action: 'Achat' },
  { entreprise: 'Qualcomm', ticker: 'QCOM', secteur: 'Technologie', valeur: '$50K-$100K', pct: 11.0, declaration: '2024-09-17', action: 'Achat' },
  { entreprise: 'Intel Corp.', ticker: 'INTC', secteur: 'Technologie', valeur: '$15K-$50K', pct: 9.0, declaration: '2024-08-26', action: 'Vente' },
  { entreprise: 'Broadcom Inc.', ticker: 'AVGO', secteur: 'Technologie', valeur: '$15K-$50K', pct: 7.0, declaration: '2024-07-15', action: 'Achat' },
];

const MOCK_MAP = {
  pelosi: PELOSI_MOCK,
  greene: GREENE_MOCK,
  schultz: SCHULTZ_MOCK,
  gottheimer: GOTTHEIMER_MOCK,
  crenshaw: CRENSHAW_MOCK,
  aoc: AOC_MOCK,
  khanna: KHANNA_MOCK,
};

const REPRESENTATIVE_NAME_MAP = {
  pelosi: 'pelosi',
  greene: 'greene',
  schultz: 'schultz',
  gottheimer: 'gottheimer',
  crenshaw: 'crenshaw',
  aoc: 'ocasio',
  khanna: 'khanna',
};

function formatPelosiTransaction(tx) {
  const actionMap = { purchase: 'Achat', sale_full: 'Vente', sale_partial: 'Vente', exchange: 'Maintien' };
  return {
    entreprise: tx.asset_description || tx.ticker || 'Inconnu',
    ticker: tx.ticker || 'N/A',
    secteur: 'N/D',
    valeur: tx.amount || 'N/D',
    pct: 0,
    declaration: tx.disclosure_date || tx.transaction_date || 'N/D',
    action: actionMap[tx.type] || 'Maintien',
  };
}

async function fetchStockActData(investor) {
  const nameFragment = REPRESENTATIVE_NAME_MAP[investor];
  const res = await fetch(
    'https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json',
    { next: { revalidate: 3600 } }
  );
  if (!res.ok) throw new Error('API unavailable');
  const data = await res.json();
  const filtered = data
    .filter(
      (tx) =>
        tx.representative &&
        tx.representative.toLowerCase().includes(nameFragment) &&
        tx.ticker &&
        tx.ticker !== '--'
    )
    .slice(0, 30)
    .map(formatPelosiTransaction);
  if (filtered.length === 0) throw new Error('No data');
  return filtered;
}

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const investor = searchParams.get('investor') || '';

  if (investor === 'buffett') return NextResponse.json(BUFFETT_HOLDINGS);
  if (investor === 'burry') return NextResponse.json(BURRY_HOLDINGS);
  if (investor === 'wood') return NextResponse.json(WOOD_HOLDINGS);

  if (MOCK_MAP[investor]) {
    try {
      const data = await fetchStockActData(investor);
      return NextResponse.json(data);
    } catch {
      return NextResponse.json(MOCK_MAP[investor]);
    }
  }

  return NextResponse.json({ error: 'Invalid investor' }, { status: 400 });
}
