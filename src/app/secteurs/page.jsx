'use client';

import { useState, useEffect, useCallback } from 'react';

const SECTORS = [
  { id: 'energie', label: 'Énergie & Pétrole', emoji: '⛽', avgPE: 12.5, perfPct: +4.2 },
  { id: 'tech', label: 'Technologies', emoji: '💻', avgPE: 34.1, perfPct: +18.7 },
  { id: 'sante', label: 'Santé & Pharma', emoji: '🏥', avgPE: 19.4, perfPct: +3.1 },
  { id: 'finance', label: 'Finance', emoji: '🏦', avgPE: 18.8, perfPct: +9.4 },
  { id: 'industrie', label: 'Industrie', emoji: '🏭', avgPE: 17.1, perfPct: +5.8 },
];

const SCORE_COLORS = {
  'FORTE OPPORTUNITÉ': { bg: 'bg-emerald-600/20', text: 'text-emerald-400', border: 'border-emerald-600/30', bar: 'bg-emerald-500' },
  'OPPORTUNITÉ': { bg: 'bg-blue-600/20', text: 'text-blue-400', border: 'border-blue-600/30', bar: 'bg-blue-500' },
  'NEUTRE': { bg: 'bg-yellow-600/20', text: 'text-yellow-400', border: 'border-yellow-600/30', bar: 'bg-yellow-500' },
  'RISQUÉ': { bg: 'bg-red-600/20', text: 'text-red-400', border: 'border-red-600/30', bar: 'bg-red-500' },
};

function ScoreBadge({ score, label }) {
  const colors = SCORE_COLORS[label] || SCORE_COLORS['NEUTRE'];
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold border ${colors.bg} ${colors.text} ${colors.border}`}>
      {score}
    </span>
  );
}

function ScoreBar({ score, label }) {
  const colors = SCORE_COLORS[label] || SCORE_COLORS['NEUTRE'];
  return (
    <div className="w-full bg-gray-800 rounded-full h-1.5 mt-2">
      <div
        className={`h-1.5 rounded-full transition-all duration-500 ${colors.bar}`}
        style={{ width: `${score}%` }}
      ></div>
    </div>
  );
}

function CompanyCard({ company }) {
  const colors = SCORE_COLORS[company.label] || SCORE_COLORS['NEUTRE'];
  const isPositive = company.change >= 0;
  return (
    <div className={`bg-gray-900 border rounded-xl p-4 hover:border-indigo-500/40 transition-all ${colors.border} border`}>
      <div className="flex items-start justify-between mb-2">
        <div>
          <span className="px-2 py-0.5 bg-gray-800 rounded font-mono text-xs text-white">{company.ticker}</span>
          <p className="text-white font-medium text-sm mt-1 leading-tight">{company.entreprise}</p>
        </div>
        <ScoreBadge score={company.score} label={company.label} />
      </div>
      <div className="flex items-center justify-between mt-3">
        <span className="text-gray-300 font-semibold">${company.price?.toFixed(2)}</span>
        <span className={`text-xs font-medium ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
          {isPositive ? '+' : ''}{company.change?.toFixed(2)}%
        </span>
      </div>
      <ScoreBar score={company.score} label={company.label} />
      <div className="flex items-center justify-between mt-2">
        <span className="text-gray-600 text-xs">P/E {company.pe > 0 ? company.pe : 'N/A'}</span>
        <span className={`text-xs font-medium ${colors.text}`}>{company.label}</span>
      </div>
      <p className="text-gray-600 text-xs mt-1">{company.analyste}</p>
    </div>
  );
}

function TopOpportunityCard({ company, rank }) {
  const colors = SCORE_COLORS[company.label] || SCORE_COLORS['NEUTRE'];
  const isPositive = company.change >= 0;
  return (
    <div className={`bg-gray-900 border ${colors.border} rounded-xl p-5 relative overflow-hidden`}>
      <div className={`absolute top-0 right-0 w-24 h-24 rounded-full blur-2xl opacity-10 ${colors.bar}`}></div>
      <div className="flex items-center gap-2 mb-3">
        <span className="w-6 h-6 bg-gray-800 rounded-full flex items-center justify-center text-xs font-bold text-gray-400">
          #{rank}
        </span>
        <span className={`px-2 py-0.5 rounded-full text-xs font-bold border ${colors.bg} ${colors.text} ${colors.border}`}>
          {company.label}
        </span>
      </div>
      <div className="flex items-end justify-between">
        <div>
          <span className="px-2 py-0.5 bg-gray-800 rounded font-mono text-xs text-white">{company.ticker}</span>
          <p className="text-white font-semibold text-base mt-1">{company.entreprise}</p>
          <p className="text-gray-500 text-xs mt-0.5">P/E {company.pe > 0 ? company.pe : 'N/A'} · {company.analyste}</p>
        </div>
        <div className="text-right">
          <div className={`text-3xl font-bold ${colors.text}`}>{company.score}</div>
          <div className="text-gray-600 text-xs">/ 100</div>
        </div>
      </div>
      <div className="flex items-center justify-between mt-3">
        <span className="text-gray-300 font-medium">${company.price?.toFixed(2)}</span>
        <span className={`text-sm font-medium ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
          {isPositive ? '+' : ''}{company.change?.toFixed(2)}%
        </span>
      </div>
      <ScoreBar score={company.score} label={company.label} />
    </div>
  );
}

export default function SecteursPage() {
  const [activeSector, setActiveSector] = useState('tech');
  const [sectorData, setSectorData] = useState({});
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('all');
  const [sort, setSort] = useState('score');
  const [topOpportunities, setTopOpportunities] = useState([]);

  const fetchSector = useCallback(async (sectorId) => {
    if (sectorData[sectorId]) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/secteurs?sector=${sectorId}`);
      const data = await res.json();
      setSectorData((prev) => {
        const updated = { ...prev, [sectorId]: Array.isArray(data) ? data : [] };
        const all = Object.values(updated).flat();
        const top = [...all].sort((a, b) => b.score - a.score).slice(0, 3);
        setTopOpportunities(top);
        return updated;
      });
    } catch {
      setSectorData((prev) => ({ ...prev, [sectorId]: [] }));
    } finally {
      setLoading(false);
    }
  }, [sectorData]);

  useEffect(() => {
    fetchSector(activeSector);
  }, [activeSector]);

  useEffect(() => {
    SECTORS.forEach((s) => fetchSector(s.id));
  }, []);

  const companies = sectorData[activeSector] || [];

  const filtered = companies.filter((c) => {
    if (filter === 'opportunities') return c.score > 60;
    if (filter === 'avoid') return c.score < 30;
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    if (sort === 'score') return b.score - a.score;
    if (sort === 'change') return b.change - a.change;
    return 0;
  });

  const activeSectorInfo = SECTORS.find((s) => s.id === activeSector);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Opportunités par Secteur</h1>
        <p className="text-gray-400 text-sm mt-2">
          Scanner d&apos;opportunités cross-sectoriel — score 0-100 basé sur la valorisation, le positionnement 52S et le consensus analystes.
        </p>
      </div>

      <div className="flex items-start gap-3 bg-amber-500/10 border border-amber-500/30 rounded-xl px-4 py-3 mb-8">
        <svg className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div>
          <p className="text-amber-300 text-sm font-medium">Données et scores indicatifs</p>
          <p className="text-amber-400/70 text-xs mt-0.5">
            Les prix affichés sont mis à jour en temps réel via Finnhub lorsqu&apos;une clé API est configurée. Les scores d&apos;opportunité sont calculés algorithmiquement à partir de données historiques — ils ne constituent pas un conseil en investissement.
          </p>
        </div>
      </div>

      {topOpportunities.length > 0 && (
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
            <h2 className="text-white font-semibold">Top 3 Opportunités du Moment</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {topOpportunities.map((c, i) => (
              <TopOpportunityCard key={c.ticker} company={c} rank={i + 1} />
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-2 overflow-x-auto pb-2 mb-6 scrollbar-hide">
        {SECTORS.map((s) => (
          <button
            key={s.id}
            onClick={() => setActiveSector(s.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
              activeSector === s.id
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700'
            }`}
          >
            <span>{s.emoji}</span>
            {s.label}
          </button>
        ))}
      </div>

      {activeSectorInfo && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-6">
          <div className="flex flex-wrap items-center gap-6">
            <div>
              <p className="text-gray-500 text-xs uppercase tracking-wider">Secteur</p>
              <p className="text-white font-semibold mt-0.5">{activeSectorInfo.emoji} {activeSectorInfo.label}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs uppercase tracking-wider">P/E Moyen</p>
              <p className="text-white font-semibold mt-0.5">{activeSectorInfo.avgPE}x</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs uppercase tracking-wider">Perf. 12 mois</p>
              <p className={`font-semibold mt-0.5 ${activeSectorInfo.perfPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {activeSectorInfo.perfPct >= 0 ? '+' : ''}{activeSectorInfo.perfPct}%
              </p>
            </div>
            <div>
              <p className="text-gray-500 text-xs uppercase tracking-wider">Tendance</p>
              <p className={`font-semibold mt-0.5 text-xl ${activeSectorInfo.perfPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {activeSectorInfo.perfPct >= 0 ? '↗' : '↘'}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div className="flex gap-2">
          {[
            { id: 'all', label: 'Toutes' },
            { id: 'opportunities', label: 'Opportunités' },
            { id: 'avoid', label: 'À éviter' },
          ].map((f) => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filter === f.id
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              {f.label}
              {f.id !== 'all' && (
                <span className="ml-1.5 px-1.5 py-0.5 rounded-full bg-gray-700 text-gray-300 text-xs">
                  {f.id === 'opportunities'
                    ? companies.filter((c) => c.score > 60).length
                    : companies.filter((c) => c.score < 30).length}
                </span>
              )}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-gray-500 text-xs">Trier par</span>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-gray-300 text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-indigo-500"
          >
            <option value="score">Score</option>
            <option value="change">Variation %</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {[...Array(7)].map((_, i) => (
            <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-4 animate-pulse">
              <div className="flex justify-between mb-3">
                <div className="h-4 w-16 bg-gray-800 rounded"></div>
                <div className="h-4 w-8 bg-gray-800 rounded-full"></div>
              </div>
              <div className="h-5 w-32 bg-gray-800 rounded mb-3"></div>
              <div className="h-3 w-full bg-gray-800 rounded-full"></div>
            </div>
          ))}
        </div>
      ) : sorted.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500 text-sm">Aucune entreprise ne correspond à ce filtre.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {sorted.map((company) => (
            <CompanyCard key={company.ticker} company={company} />
          ))}
        </div>
      )}
    </div>
  );
}
