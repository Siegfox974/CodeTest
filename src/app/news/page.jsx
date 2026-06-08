'use client';

import { useState, useEffect, useCallback } from 'react';
import NewsCard from '@/components/NewsCard';

const ALL_SYMBOLS = ['AAPL', 'NVDA', 'MSFT', 'GOOGL', 'META', 'TSLA', 'AMZN', 'JPM', 'JNJ', 'XOM', 'WMT', 'BRK.B', 'PG', 'V'];

export default function NewsPage() {
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [lastUpdate, setLastUpdate] = useState(null);
  const [countdown, setCountdown] = useState(300);

  const fetchNews = useCallback(async () => {
    try {
      const res = await fetch(`/api/news?symbols=${ALL_SYMBOLS.join(',')}`);
      const data = await res.json();
      if (Array.isArray(data)) setNews(data);
      setLastUpdate(new Date());
      setCountdown(300);
    } catch {
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNews();
    const interval = setInterval(fetchNews, 300000);
    return () => clearInterval(interval);
  }, [fetchNews]);

  useEffect(() => {
    if (countdown <= 0) return;
    const t = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [countdown]);

  const filtered = news.filter((item) => {
    const matchSymbol = selectedSymbol ? item.symbol === selectedSymbol : true;
    const matchSearch = search
      ? (item.headline || '').toLowerCase().includes(search.toLowerCase()) ||
        (item.symbol || '').toLowerCase().includes(search.toLowerCase())
      : true;
    return matchSymbol && matchSearch;
  });

  const sentimentCounts = news.reduce(
    (acc, item) => {
      acc[item.sentiment] = (acc[item.sentiment] || 0) + 1;
      return acc;
    },
    { positive: 0, negative: 0, neutral: 0 }
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Actualités Financières</h1>
          <p className="text-gray-400 text-sm mt-1">
            {lastUpdate
              ? `Mis à jour : ${lastUpdate.toLocaleTimeString('fr-FR')} — actualisation dans ${Math.floor(countdown / 60)}m${countdown % 60}s`
              : 'Chargement...'}
          </p>
        </div>
        {!loading && (
          <div className="flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              {sentimentCounts.positive} positif
            </span>
            <span className="flex items-center gap-1.5 text-yellow-400">
              <span className="w-1.5 h-1.5 rounded-full bg-yellow-400"></span>
              {sentimentCounts.neutral} neutre
            </span>
            <span className="flex items-center gap-1.5 text-red-400">
              <span className="w-1.5 h-1.5 rounded-full bg-red-400"></span>
              {sentimentCounts.negative} négatif
            </span>
          </div>
        )}
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Rechercher dans les titres..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </div>
        <select
          value={selectedSymbol}
          onChange={(e) => setSelectedSymbol(e.target.value)}
          className="bg-gray-900 border border-gray-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors appearance-none pr-8"
        >
          <option value="">Toutes les entreprises</option>
          {ALL_SYMBOLS.map((sym) => (
            <option key={sym} value={sym}>{sym}</option>
          ))}
        </select>
        {(search || selectedSymbol) && (
          <button
            onClick={() => { setSearch(''); setSelectedSymbol(''); }}
            className="px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-xl text-sm text-gray-400 hover:text-white hover:border-gray-600 transition-colors whitespace-nowrap"
          >
            Effacer
          </button>
        )}
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-gray-400 text-sm">Chargement des actualités...</p>
          </div>
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-48 text-gray-500">
          <svg className="w-12 h-12 mb-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
          </svg>
          <p className="text-sm">Aucune actualité trouvée</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map((item) => (
            <NewsCard key={item.id || `${item.symbol}-${item.datetime}`} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
