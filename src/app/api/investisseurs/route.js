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
  { entreprise: 'AllianceBernstein', ticker: 'AB', secteur: 'Finance', valeur: '$500K-$1M', pct: 6.0, declaration: '2024-07-22', action: 'Achat' },
  { entreprise: 'Palo Alto Networks', ticker: 'PANW', secteur: 'Technologie', valeur: '$250K-$500K', pct: 5.0, declaration: '2024-06-14', action: 'Achat' },
];

function formatPelosiTransaction(tx) {
  const actionMap = { purchase: 'Achat', sale_full: 'Vente', sale_partial: 'Vente', exchange: 'Maintien' };
  return {
    entreprise: tx.asset_description || tx.ticker || 'Inconnu',
    ticker: tx.ticker || 'N/A',
    secteur: 'Technologie',
    valeur: tx.amount || 'N/D',
    pct: 0,
    declaration: tx.disclosure_date || tx.transaction_date || 'N/D',
    action: actionMap[tx.type] || 'Maintien',
  };
}

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const investor = searchParams.get('investor') || '';

  if (investor === 'buffett') return NextResponse.json(BUFFETT_HOLDINGS);
  if (investor === 'burry') return NextResponse.json(BURRY_HOLDINGS);
  if (investor === 'wood') return NextResponse.json(WOOD_HOLDINGS);

  if (investor === 'pelosi') {
    try {
      const res = await fetch(
        'https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json',
        { next: { revalidate: 3600 } }
      );
      if (!res.ok) throw new Error('API unavailable');
      const data = await res.json();
      const pelosi = data
        .filter(
          (tx) =>
            tx.representative &&
            tx.representative.toLowerCase().includes('pelosi') &&
            tx.ticker &&
            tx.ticker !== '--'
        )
        .slice(0, 50)
        .map(formatPelosiTransaction);
      if (pelosi.length === 0) throw new Error('No data');
      return NextResponse.json(pelosi);
    } catch {
      return NextResponse.json(PELOSI_MOCK);
    }
  }

  return NextResponse.json({ error: 'Invalid investor' }, { status: 400 });
}
