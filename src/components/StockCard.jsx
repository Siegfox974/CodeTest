'use client';

import StockChart from './StockChart';

function formatVolume(vol) {
  if (vol >= 1_000_000) return `${(vol / 1_000_000).toFixed(1)}M`;
  if (vol >= 1_000) return `${(vol / 1_000).toFixed(0)}K`;
  return String(vol);
}

export default function StockCard({ stock }) {
  const isPositive = stock.changePct >= 0;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 hover:border-indigo-500/50 hover:bg-gray-800/60 transition-all duration-200 cursor-default">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-white font-bold text-base">{stock.symbol}</span>
            <span
              className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                isPositive ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
              }`}
            >
              {isPositive ? '+' : ''}{stock.changePct.toFixed(2)}%
            </span>
          </div>
          <p className="text-gray-400 text-xs truncate max-w-[140px]">{stock.name}</p>
        </div>
        <div className="text-right">
          <p className="text-white font-semibold text-base">${stock.price.toFixed(2)}</p>
          <p className={`text-xs font-medium ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
            {isPositive ? '+' : ''}${stock.change.toFixed(2)}
          </p>
        </div>
      </div>

      {stock.sparkline && stock.sparkline.length > 1 && (
        <div className="mb-3">
          <StockChart prices={stock.sparkline} positive={isPositive} height={52} />
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>Vol: {formatVolume(stock.volume)}</span>
        {stock.high52 > 0 && (
          <span className="text-gray-600">52W: {stock.low52.toFixed(0)}–{stock.high52.toFixed(0)}</span>
        )}
      </div>
    </div>
  );
}
