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
  const hasUrl = item.url && item.url !== '#';

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 hover:border-indigo-500/50 hover:bg-gray-800/60 transition-all duration-200 flex flex-col">
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

      <div className="flex items-center justify-between mt-auto pt-3 border-t border-gray-800">
        <div className="flex items-center gap-2">
          <span className="bg-indigo-600/20 text-indigo-400 text-xs font-medium px-2 py-0.5 rounded border border-indigo-500/30">
            {item.symbol}
          </span>
          <span className="text-gray-500 text-xs">{item.source}</span>
          <span className="text-gray-600 text-xs">{formatDate(item.datetime)}</span>
        </div>
        {hasUrl ? (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 font-medium transition-colors whitespace-nowrap"
          >
            Lire l'article
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        ) : (
          <span className="text-xs text-gray-600 italic flex items-center gap-1">
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
            </svg>
            Titre simulé — activez votre clé API pour les vrais articles
          </span>
        )}
      </div>
    </div>
  );
}
