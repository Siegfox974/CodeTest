'use client';

import { useState, useEffect, useCallback } from 'react';
import StockCard from '@/components/StockCard';

const TECH = ['AAPL', 'NVDA', 'MSFT', 'GOOGL', 'META', 'TSLA', 'AMZN'];
const OTHER = ['JPM', 'JNJ', 'XOM', 'WMT', 'BRK.B', 'PG', 'V'];

function RefreshCountdown({ seconds }) {
  return (
    <span className="text-xs text-gray-500">
      Actualisation dans {seconds}s
    </span>
  );
}

export default function DashboardPage() {
  const [techStocks, setTechStocks] = useState([]);
  const [otherStocks, setOtherStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [countdown, setCountdown] = useState(60);

  const fetchStocks = useCallback(async () => {
    try {
      const [techRes, otherRes] = await Promise.all([
        fetch(`/api/stocks?symbols=${TECH.join(',')}`),
        fetch(`/api/stocks?symbols=${OTHER.join(',')}`),
      ]);
      const [techData, otherData] = await Promise.all([techRes.json(), otherRes.json()]);
      if (Array.isArray(techData)) setTechStocks(techData);
      if (Array.isArray(otherData)) setOtherStocks(otherData);
      setLastUpdate(new Date());
      setCountdown(60);
    } catch {
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStocks();
    const interval = setInterval(fetchStocks, 60000);
    return () => clearInterval(interval);
  }, [fetchStocks]);

  useEffect(() => {
    if (countdown <= 0) return;
    const t = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [countdown]);

  const allPositive = [...techStocks, ...otherStocks].filter((s) => s.changePct > 0).length;
  const allNegative = [...techStocks, ...otherStocks].filter((s) => s.changePct < 0).length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Marchés Financiers</h1>
          <p className="text-gray-400 text-sm mt-1">
            {lastUpdate
              ? `Dernière mise à jour : ${lastUpdate.toLocaleTimeString('fr-FR')}`
              : 'Chargement...'}
          </p>
        </div>
        <div className="flex items-center gap-4">
          {!loading && (
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5 text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                {allPositive} en hausse
              </span>
              <span className="flex items-center gap-1.5 text-red-400">
                <span className="w-1.5 h-1.5 rounded-full bg-red-400"></span>
                {allNegative} en baisse
              </span>
            </div>
          )}
          <RefreshCountdown seconds={countdown} />
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-gray-400 text-sm">Chargement des données...</p>
          </div>
        </div>
      ) : (
        <>
          <section className="mb-10">
            <div className="flex items-center gap-3 mb-4">
              <h2 className="text-lg font-semibold text-white">Tech Giants</h2>
              <span className="px-2 py-0.5 bg-indigo-600/20 text-indigo-400 text-xs rounded-full border border-indigo-600/30">
                {TECH.length} entreprises
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {techStocks.map((stock) => (
                <StockCard key={stock.symbol} stock={stock} />
              ))}
            </div>
          </section>

          <section>
            <div className="flex items-center gap-3 mb-4">
              <h2 className="text-lg font-semibold text-white">Autres Secteurs</h2>
              <span className="px-2 py-0.5 bg-gray-700/50 text-gray-400 text-xs rounded-full border border-gray-700">
                {OTHER.length} entreprises
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {otherStocks.map((stock) => (
                <StockCard key={stock.symbol} stock={stock} />
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
