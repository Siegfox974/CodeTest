'use client';

import { useState, useCallback } from 'react';
import AnalyseCard from '@/components/AnalyseCard';

const ALL_SYMBOLS = [
  { symbol: 'AAPL', name: 'Apple Inc.' },
  { symbol: 'NVDA', name: 'NVIDIA Corp.' },
  { symbol: 'MSFT', name: 'Microsoft Corp.' },
  { symbol: 'GOOGL', name: 'Alphabet Inc.' },
  { symbol: 'META', name: 'Meta Platforms' },
  { symbol: 'TSLA', name: 'Tesla Inc.' },
  { symbol: 'AMZN', name: 'Amazon.com Inc.' },
  { symbol: 'JPM', name: 'JPMorgan Chase' },
  { symbol: 'JNJ', name: 'Johnson & Johnson' },
  { symbol: 'XOM', name: 'Exxon Mobil Corp.' },
  { symbol: 'WMT', name: 'Walmart Inc.' },
  { symbol: 'BRK.B', name: 'Berkshire Hathaway' },
  { symbol: 'PG', name: 'Procter & Gamble' },
  { symbol: 'V', name: 'Visa Inc.' },
];

export default function AnalysePage() {
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchAnalysis = useCallback(async (symbol) => {
    if (!symbol) return;
    setLoading(true);
    setError(null);
    setAnalysis(null);
    try {
      const res = await fetch(`/api/analyse?symbol=${symbol}`);
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setAnalysis(data);
    } catch (err) {
      setError(err.message || 'Erreur lors de la récupération des données');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSymbolChange = (e) => {
    const sym = e.target.value;
    setSelectedSymbol(sym);
    fetchAnalysis(sym);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-1">Analyse Technique</h1>
        <p className="text-gray-400 text-sm">
          Analyse approfondie avec indicateurs RSI, MACD, moyennes mobiles et sentiment des actualités.
        </p>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 mb-6">
        <label className="block text-gray-400 text-sm font-medium mb-3">Sélectionner une entreprise</label>
        <div className="flex flex-col sm:flex-row gap-3">
          <select
            value={selectedSymbol}
            onChange={handleSymbolChange}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-indigo-500 transition-colors appearance-none"
          >
            <option value="">-- Choisir une entreprise --</option>
            <optgroup label="Tech Giants">
              {ALL_SYMBOLS.slice(0, 7).map(({ symbol, name }) => (
                <option key={symbol} value={symbol}>{symbol} — {name}</option>
              ))}
            </optgroup>
            <optgroup label="Autres Secteurs">
              {ALL_SYMBOLS.slice(7).map(({ symbol, name }) => (
                <option key={symbol} value={symbol}>{symbol} — {name}</option>
              ))}
            </optgroup>
          </select>
          {selectedSymbol && (
            <button
              onClick={() => fetchAnalysis(selectedSymbol)}
              disabled={loading}
              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-xl transition-colors whitespace-nowrap"
            >
              {loading ? 'Analyse...' : 'Actualiser'}
            </button>
          )}
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {ALL_SYMBOLS.map(({ symbol }) => (
            <button
              key={symbol}
              onClick={() => {
                setSelectedSymbol(symbol);
                fetchAnalysis(symbol);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                selectedSymbol === symbol
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white border border-gray-700'
              }`}
            >
              {symbol}
            </button>
          ))}
        </div>
      </div>

      {!selectedSymbol && !loading && !analysis && (
        <div className="flex flex-col items-center justify-center h-64 text-gray-600">
          <svg className="w-16 h-16 mb-4 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p className="text-sm">Sélectionnez une entreprise pour voir l&apos;analyse</p>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-gray-400 text-sm">Calcul des indicateurs en cours...</p>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">
          <strong>Erreur :</strong> {error}
        </div>
      )}

      {analysis && !loading && (
        <AnalyseCard data={analysis} />
      )}
    </div>
  );
}
