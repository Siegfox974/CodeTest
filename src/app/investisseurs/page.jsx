'use client';

import { useState, useEffect, useCallback } from 'react';

const INVESTORS = [
  {
    id: 'pelosi',
    nom: 'Nancy Pelosi',
    titre: 'Représentante US, Californie',
    fond: 'Portefeuille personnel',
    badge: 'STOCK Act',
    badgeColor: 'bg-blue-600/20 text-blue-400 border-blue-600/30',
    initiales: 'NP',
    avatarColor: 'bg-blue-700',
    description: 'Divulgation obligatoire sous le STOCK Act (2012) — transactions dans les 45 jours.',
  },
  {
    id: 'buffett',
    nom: 'Warren Buffett',
    titre: 'PDG, Berkshire Hathaway',
    fond: 'Berkshire Hathaway',
    badge: '13F SEC',
    badgeColor: 'bg-amber-600/20 text-amber-400 border-amber-600/30',
    initiales: 'WB',
    avatarColor: 'bg-amber-700',
    description: 'Dépôt 13F trimestriel obligatoire auprès de la SEC pour les gestionnaires >$100M.',
  },
  {
    id: 'burry',
    nom: 'Michael Burry',
    titre: 'Fondateur, Scion Asset Mgmt',
    fond: 'Scion Asset Management',
    badge: '13F SEC',
    badgeColor: 'bg-amber-600/20 text-amber-400 border-amber-600/30',
    initiales: 'MB',
    avatarColor: 'bg-red-800',
    description: 'Dépôt 13F trimestriel — connu pour avoir prédit la crise des subprimes de 2008.',
  },
  {
    id: 'wood',
    nom: 'Cathie Wood',
    titre: 'Fondatrice & CEO, ARK Invest',
    fond: 'ARK Investment Management',
    badge: 'ARK Daily',
    badgeColor: 'bg-emerald-600/20 text-emerald-400 border-emerald-600/30',
    initiales: 'CW',
    avatarColor: 'bg-emerald-700',
    description: 'ARK Invest publie ses transactions quotidiennement — transparence totale unique dans le secteur.',
  },
];

function ActionBadge({ action }) {
  if (action === 'Achat') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-600/20 text-emerald-400 border border-emerald-600/30">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
        Achat
      </span>
    );
  }
  if (action === 'Vente') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-red-600/20 text-red-400 border border-red-600/30">
        <span className="w-1.5 h-1.5 rounded-full bg-red-400"></span>
        Vente
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-600/20 text-gray-400 border border-gray-600/30">
      <span className="w-1.5 h-1.5 rounded-full bg-gray-400"></span>
      Maintien
    </span>
  );
}

function SkeletonRow() {
  return (
    <tr className="border-t border-gray-800">
      {[...Array(7)].map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 bg-gray-800 rounded animate-pulse"></div>
        </td>
      ))}
    </tr>
  );
}

export default function InvestisseursPage() {
  const [selectedInvestor, setSelectedInvestor] = useState(null);
  const [portfolios, setPortfolios] = useState({});
  const [loadingId, setLoadingId] = useState(null);
  const [compareIds, setCompareIds] = useState([]);

  const fetchPortfolio = useCallback(async (id) => {
    if (portfolios[id]) return;
    setLoadingId(id);
    try {
      const res = await fetch(`/api/investisseurs?investor=${id}`);
      const data = await res.json();
      setPortfolios((prev) => ({ ...prev, [id]: Array.isArray(data) ? data : [] }));
    } catch {
      setPortfolios((prev) => ({ ...prev, [id]: [] }));
    } finally {
      setLoadingId(null);
    }
  }, [portfolios]);

  const handleSelectInvestor = (investor) => {
    setSelectedInvestor(investor);
    fetchPortfolio(investor.id);
  };

  const toggleCompare = (id) => {
    setCompareIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
    fetchPortfolio(id);
  };

  const sharedHoldings = () => {
    if (compareIds.length < 2) return [];
    const tickerCount = {};
    const tickerInfo = {};
    compareIds.forEach((id) => {
      const holdings = portfolios[id] || [];
      holdings.forEach((h) => {
        if (!tickerCount[h.ticker]) {
          tickerCount[h.ticker] = 0;
          tickerInfo[h.ticker] = h;
        }
        tickerCount[h.ticker]++;
      });
    });
    return Object.entries(tickerCount)
      .filter(([, count]) => count >= 2)
      .map(([ticker, count]) => ({ ...tickerInfo[ticker], sharedCount: count }))
      .sort((a, b) => b.sharedCount - a.sharedCount);
  };

  const currentHoldings = selectedInvestor ? (portfolios[selectedInvestor.id] || []) : [];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Investisseurs Emblématiques</h1>
        <p className="text-gray-400 text-sm mt-2 max-w-3xl">
          Suivez les portefeuilles des investisseurs les plus influents. Les données sont issues de divulgations légales obligatoires : STOCK Act (élus américains), dépôts 13F SEC (gestionnaires institutionnels) et publications quotidiennes ARK Invest.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {INVESTORS.map((investor) => (
          <div
            key={investor.id}
            onClick={() => handleSelectInvestor(investor)}
            className={`bg-gray-900 border rounded-xl p-5 cursor-pointer transition-all hover:border-indigo-500/50 ${
              selectedInvestor?.id === investor.id
                ? 'border-indigo-500 ring-1 ring-indigo-500/30'
                : 'border-gray-800'
            }`}
          >
            <div className="flex items-start justify-between mb-4">
              <div
                className={`w-12 h-12 rounded-xl ${investor.avatarColor} flex items-center justify-center`}
              >
                <span className="text-white font-bold text-sm">{investor.initiales}</span>
              </div>
              <span
                className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${investor.badgeColor}`}
              >
                {investor.badge}
              </span>
            </div>
            <h3 className="text-white font-semibold text-sm">{investor.nom}</h3>
            <p className="text-gray-500 text-xs mt-0.5">{investor.titre}</p>
            <p className="text-gray-600 text-xs mt-3 leading-relaxed">{investor.description}</p>
            <div className="mt-4 flex items-center justify-between">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  toggleCompare(investor.id);
                }}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                  compareIds.includes(investor.id)
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                {compareIds.includes(investor.id) ? 'Comparé' : 'Comparer'}
              </button>
              {loadingId === investor.id && (
                <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
              )}
            </div>
          </div>
        ))}
      </div>

      {selectedInvestor && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-8">
          <div className="flex items-center gap-3 mb-6">
            <div className={`w-10 h-10 rounded-lg ${selectedInvestor.avatarColor} flex items-center justify-center`}>
              <span className="text-white font-bold text-sm">{selectedInvestor.initiales}</span>
            </div>
            <div>
              <h2 className="text-white font-semibold">{selectedInvestor.nom}</h2>
              <p className="text-gray-500 text-xs">{selectedInvestor.fond}</p>
            </div>
            <span className={`ml-auto px-2 py-0.5 rounded-full text-xs font-semibold border ${selectedInvestor.badgeColor}`}>
              {selectedInvestor.badge}
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left">
                  <th className="px-4 py-2 text-gray-500 font-medium text-xs uppercase tracking-wider">Entreprise</th>
                  <th className="px-4 py-2 text-gray-500 font-medium text-xs uppercase tracking-wider">Ticker</th>
                  <th className="px-4 py-2 text-gray-500 font-medium text-xs uppercase tracking-wider">Secteur</th>
                  <th className="px-4 py-2 text-gray-500 font-medium text-xs uppercase tracking-wider">Valeur estimée</th>
                  <th className="px-4 py-2 text-gray-500 font-medium text-xs uppercase tracking-wider">% Portfolio</th>
                  <th className="px-4 py-2 text-gray-500 font-medium text-xs uppercase tracking-wider">Dernière déclaration</th>
                  <th className="px-4 py-2 text-gray-500 font-medium text-xs uppercase tracking-wider">Action</th>
                </tr>
              </thead>
              <tbody>
                {loadingId === selectedInvestor.id ? (
                  [...Array(5)].map((_, i) => <SkeletonRow key={i} />)
                ) : currentHoldings.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-gray-500 text-sm">
                      Aucune donnée disponible
                    </td>
                  </tr>
                ) : (
                  currentHoldings.map((h, i) => (
                    <tr key={i} className="border-t border-gray-800 hover:bg-gray-800/30 transition-colors">
                      <td className="px-4 py-3 text-white font-medium text-sm">{h.entreprise}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 bg-gray-800 rounded text-gray-300 font-mono text-xs">
                          {h.ticker}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-sm">{h.secteur}</td>
                      <td className="px-4 py-3 text-gray-300 text-sm">{h.valeur}</td>
                      <td className="px-4 py-3">
                        {h.pct > 0 ? (
                          <div className="flex items-center gap-2">
                            <div className="w-16 bg-gray-800 rounded-full h-1.5">
                              <div
                                className="bg-indigo-500 h-1.5 rounded-full"
                                style={{ width: `${Math.min(100, h.pct * 2)}%` }}
                              ></div>
                            </div>
                            <span className="text-gray-300 text-sm">{h.pct.toFixed(1)}%</span>
                          </div>
                        ) : (
                          <span className="text-gray-500 text-sm">N/D</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-sm">{h.declaration}</td>
                      <td className="px-4 py-3">
                        <ActionBadge action={h.action} />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {compareIds.length >= 2 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-8 h-8 bg-indigo-600/20 rounded-lg flex items-center justify-center">
              <svg className="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <h2 className="text-white font-semibold">Entreprises en commun</h2>
              <p className="text-gray-500 text-xs">
                Tickers détenus par plusieurs investisseurs sélectionnés ({compareIds.length} comparés)
              </p>
            </div>
            <div className="ml-auto flex gap-2">
              {compareIds.map((id) => {
                const inv = INVESTORS.find((i) => i.id === id);
                return (
                  <div key={id} className={`w-7 h-7 rounded-lg ${inv.avatarColor} flex items-center justify-center`}>
                    <span className="text-white font-bold text-xs">{inv.initiales}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {(() => {
            const shared = sharedHoldings();
            if (shared.length === 0) {
              return (
                <div className="text-center py-8">
                  <p className="text-gray-500 text-sm">Aucun titre en commun parmi les investisseurs sélectionnés.</p>
                  <p className="text-gray-600 text-xs mt-1">Essayez de charger les portfolios avant de comparer.</p>
                </div>
              );
            }
            return (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {shared.map((h) => (
                  <div key={h.ticker} className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 flex items-center gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 bg-gray-700 rounded font-mono text-xs text-white">
                          {h.ticker}
                        </span>
                        <span className="px-1.5 py-0.5 bg-indigo-600/20 text-indigo-400 border border-indigo-600/30 rounded-full text-xs font-semibold">
                          {h.sharedCount} investisseurs
                        </span>
                      </div>
                      <p className="text-gray-300 text-sm font-medium mt-1 truncate">{h.entreprise}</p>
                      <p className="text-gray-500 text-xs">{h.secteur}</p>
                    </div>
                  </div>
                ))}
              </div>
            );
          })()}
        </div>
      )}

      {compareIds.length === 1 && (
        <div className="bg-gray-900/50 border border-gray-800 border-dashed rounded-xl p-6 text-center">
          <p className="text-gray-500 text-sm">
            Sélectionnez au moins un autre investisseur à comparer pour voir les titres en commun.
          </p>
        </div>
      )}
    </div>
  );
}
