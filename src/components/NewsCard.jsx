'use client';

function formatDate(ts) {
  const d = new Date(ts * 1000);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

const sentimentConfig = {
  positive: { label: 'Positive', classes: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' },
  negative: { label: 'Negative', classes: 'bg-red-500/20 text-red-400 border border-red-500/30' },
  neutral: { label: 'Neutral', classes: 'bg-gray-700/50 text-gray-400 border border-gray-600/30' },
};

export default function NewsCard({ item }) {
  const s = sentimentConfig[item.sentiment] || sentimentConfig.neutral;

  return (
    <a
      href={item.url && item.url !== '#' ? item.url : undefined}
      target="_blank"
      rel="noopener noreferrer"
      className="block bg-gray-900 border border-gray-800 rounded-xl p-4 hover:border-indigo-500/50 hover:bg-gray-800/60 transition-all duration-200"
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <h3 className="text-white font-medium text-sm leading-snug line-clamp-2 flex-1">
          {item.headline}
        </h3>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap ${s.classes}`}>
          {s.label}
        </span>
      </div>

      {item.summary && (
        <p className="text-gray-400 text-xs leading-relaxed line-clamp-2 mb-3">{item.summary}</p>
      )}

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="bg-indigo-600/20 text-indigo-400 text-xs font-medium px-2 py-0.5 rounded border border-indigo-500/30">
            {item.symbol}
          </span>
          <span className="text-gray-500 text-xs">{item.source}</span>
        </div>
        <span className="text-gray-600 text-xs">{formatDate(item.datetime)}</span>
      </div>
    </a>
  );
}
