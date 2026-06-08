'use client';

import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(LineElement, PointElement, LinearScale, CategoryScale, Filler, Tooltip, Legend);

function RSIGauge({ rsi }) {
  if (rsi === null || rsi === undefined) return <span className="text-gray-500">N/A</span>;
  let color = 'text-yellow-400';
  let label = 'Neutral';
  if (rsi < 30) { color = 'text-emerald-400'; label = 'Oversold'; }
  else if (rsi > 70) { color = 'text-red-400'; label = 'Overbought'; }
  else if (rsi < 45) { color = 'text-emerald-300'; label = 'Slightly Oversold'; }
  else if (rsi > 55) { color = 'text-orange-400'; label = 'Slightly Overbought'; }

  return (
    <div className="flex items-center gap-2">
      <span className={`font-bold text-lg ${color}`}>{rsi.toFixed(1)}</span>
      <span className={`text-xs ${color}`}>{label}</span>
    </div>
  );
}

function ScoreMeter({ score }) {
  const pct = Math.max(0, Math.min(100, score));
  let barColor = 'bg-yellow-500';
  if (pct >= 75) barColor = 'bg-emerald-500';
  else if (pct >= 60) barColor = 'bg-green-500';
  else if (pct <= 25) barColor = 'bg-red-500';
  else if (pct <= 40) barColor = 'bg-orange-500';

  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-gray-400 mb-1">
        <span>0</span>
        <span className="font-bold text-white">{pct}/100</span>
        <span>100</span>
      </div>
      <div className="h-3 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

const recommendationStyles = {
  'FORT SIGNAL D\'ACHAT': 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50',
  'SIGNAL D\'ACHAT': 'bg-green-500/20 text-green-400 border-green-500/50',
  'NEUTRE': 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50',
  'SIGNAL DE VENTE': 'bg-orange-500/20 text-orange-400 border-orange-500/50',
  'FORT SIGNAL DE VENTE': 'bg-red-500/20 text-red-400 border-red-500/50',
};

export default function AnalyseCard({ data }) {
  const recStyle = recommendationStyles[data.recommendation?.label] || 'bg-gray-700 text-gray-300 border-gray-600';

  const chartData = data.closePrices && data.closePrices.length > 1 ? {
    labels: data.closePrices.map((_, i) => i + 1),
    datasets: [
      {
        label: 'Price',
        data: data.closePrices,
        borderColor: '#6366f1',
        backgroundColor: 'rgba(99,102,241,0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: '#6366f1',
      },
    ],
  } : null;

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: { label: (ctx) => `$${ctx.parsed.y.toFixed(2)}` },
        backgroundColor: 'rgba(15,15,25,0.9)',
        titleColor: '#9ca3af',
        bodyColor: '#fff',
        borderColor: 'rgba(99,102,241,0.3)',
        borderWidth: 1,
        displayColors: false,
      },
    },
    scales: {
      x: { display: false },
      y: {
        display: true,
        grid: { color: 'rgba(255,255,255,0.05)' },
        ticks: { color: '#6b7280', font: { size: 10 }, callback: (v) => `$${v.toFixed(0)}` },
      },
    },
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
      <div className="p-6 border-b border-gray-800">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h2 className="text-2xl font-bold text-white">{data.symbol}</h2>
              <span className="text-gray-400 text-sm">{data.name}</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-white">${data.price?.toFixed(2)}</span>
            </div>
          </div>
          <div className={`border rounded-xl px-5 py-3 text-center ${recStyle}`}>
            <p className="text-xs opacity-70 mb-0.5">Signal</p>
            <p className="font-bold text-sm leading-tight">{data.recommendation?.label}</p>
          </div>
        </div>
      </div>

      {chartData && (
        <div className="px-6 pt-4 pb-2">
          <p className="text-gray-500 text-xs mb-2">30-day price history</p>
          <div style={{ height: 140 }}>
            <Line data={chartData} options={chartOptions} />
          </div>
        </div>
      )}

      <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-gray-800/50 rounded-xl p-4">
          <p className="text-gray-400 text-xs mb-1">52-Week Range</p>
          <div className="flex items-center gap-2">
            <span className="text-red-400 font-medium">${data.low52?.toFixed(2)}</span>
            <div className="flex-1 h-1.5 bg-gray-700 rounded-full relative">
              {data.price && data.high52 && data.low52 && (
                <div
                  className="absolute top-0 h-full w-1.5 bg-indigo-400 rounded-full -translate-x-1/2"
                  style={{
                    left: `${Math.max(0, Math.min(100, ((data.price - data.low52) / (data.high52 - data.low52)) * 100))}%`,
                  }}
                />
              )}
            </div>
            <span className="text-emerald-400 font-medium">${data.high52?.toFixed(2)}</span>
          </div>
        </div>

        <div className="bg-gray-800/50 rounded-xl p-4">
          <p className="text-gray-400 text-xs mb-1">RSI (14)</p>
          <RSIGauge rsi={data.rsi} />
        </div>

        <div className="bg-gray-800/50 rounded-xl p-4">
          <p className="text-gray-400 text-xs mb-2">MACD</p>
          {data.macd ? (
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-gray-500">MACD</span>
                <span className={data.macd.macd >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                  {data.macd.macd.toFixed(4)}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-500">Signal</span>
                <span className="text-gray-300">{data.macd.signal.toFixed(4)}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-500">Histogram</span>
                <span className={data.macd.histogram >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                  {data.macd.histogram.toFixed(4)}
                </span>
              </div>
              <div className={`text-xs font-medium mt-1 ${data.macd.bullish ? 'text-emerald-400' : 'text-red-400'}`}>
                {data.macd.bullish ? 'Bullish crossover' : 'Bearish crossover'}
              </div>
            </div>
          ) : (
            <span className="text-gray-500 text-sm">N/A</span>
          )}
        </div>

        <div className="bg-gray-800/50 rounded-xl p-4">
          <p className="text-gray-400 text-xs mb-2">Moving Averages</p>
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">MA50</span>
              <span className="text-gray-200">{data.ma50 !== null ? `$${data.ma50?.toFixed(2)}` : 'N/A'}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">MA200</span>
              <span className="text-gray-200">{data.ma200 !== null ? `$${data.ma200?.toFixed(2)}` : 'N/A'}</span>
            </div>
            {data.goldenCross && (
              <div className="text-xs text-emerald-400 font-medium">Golden Cross</div>
            )}
            {data.deathCross && (
              <div className="text-xs text-red-400 font-medium">Death Cross</div>
            )}
          </div>
        </div>

        <div className="bg-gray-800/50 rounded-xl p-4 sm:col-span-2">
          <p className="text-gray-400 text-xs mb-2">News Sentiment (7 days)</p>
          <div className="flex items-center gap-3">
            <div className={`text-lg font-bold ${
              data.sentimentScore > 0.15 ? 'text-emerald-400' :
              data.sentimentScore < -0.15 ? 'text-red-400' : 'text-yellow-400'
            }`}>
              {data.sentimentScore > 0 ? '+' : ''}{(data.sentimentScore * 100).toFixed(0)}
            </div>
            <div className="flex-1 h-2 bg-gray-700 rounded-full relative overflow-hidden">
              <div className="absolute inset-0 flex">
                <div className="flex-1 bg-red-500/20" />
                <div className="flex-1 bg-yellow-500/20" />
                <div className="flex-1 bg-emerald-500/20" />
              </div>
              <div
                className={`absolute top-0 h-full w-2 rounded-full -translate-x-1/2 ${
                  data.sentimentScore > 0.15 ? 'bg-emerald-400' :
                  data.sentimentScore < -0.15 ? 'bg-red-400' : 'bg-yellow-400'
                }`}
                style={{ left: `${50 + (data.sentimentScore || 0) * 50}%` }}
              />
            </div>
            <span className={`text-xs ${
              data.sentimentScore > 0.15 ? 'text-emerald-400' :
              data.sentimentScore < -0.15 ? 'text-red-400' : 'text-yellow-400'
            }`}>
              {data.sentimentScore > 0.15 ? 'Positive' : data.sentimentScore < -0.15 ? 'Negative' : 'Neutral'}
            </span>
          </div>
        </div>

        <div className="bg-gray-800/50 rounded-xl p-4 sm:col-span-2">
          <p className="text-gray-400 text-xs mb-3">Overall Score</p>
          <ScoreMeter score={data.overallScore} />
        </div>
      </div>

      <div className="px-6 pb-6">
        <div className="bg-yellow-500/5 border border-yellow-500/20 rounded-xl p-4">
          <p className="text-yellow-500/80 text-xs font-medium mb-1">Avertissement légal</p>
          <p className="text-yellow-500/60 text-xs leading-relaxed">
            Les informations fournies sur cette plateforme sont à titre purement informatif et éducatif. Elles ne constituent pas un conseil en investissement, une recommandation d&apos;achat ou de vente de titres financiers. Les performances passées ne garantissent pas les résultats futurs. Tout investissement comporte un risque de perte en capital. Consultez un conseiller financier agréé avant toute décision d&apos;investissement.
          </p>
        </div>
      </div>
    </div>
  );
}
