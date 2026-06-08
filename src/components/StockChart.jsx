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
} from 'chart.js';

ChartJS.register(LineElement, PointElement, LinearScale, CategoryScale, Filler, Tooltip);

export default function StockChart({ prices = [], positive = true, height = 60 }) {
  const color = positive ? '#34d399' : '#f87171';
  const colorAlpha = positive ? 'rgba(52,211,153,0.15)' : 'rgba(248,113,113,0.15)';

  const data = {
    labels: prices.map((_, i) => i),
    datasets: [
      {
        data: prices,
        borderColor: color,
        borderWidth: 1.5,
        fill: true,
        backgroundColor: colorAlpha,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 3,
        pointHoverBackgroundColor: color,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx) => `$${ctx.parsed.y.toFixed(2)}`,
        },
        displayColors: false,
        backgroundColor: 'rgba(15,15,25,0.9)',
        titleColor: '#9ca3af',
        bodyColor: '#fff',
        borderColor: 'rgba(99,102,241,0.3)',
        borderWidth: 1,
      },
    },
    scales: {
      x: { display: false },
      y: { display: false },
    },
    animation: false,
  };

  return (
    <div style={{ height }}>
      <Line data={data} options={options} />
    </div>
  );
}
