import { useRef, useEffect } from 'react';
import gsap from 'gsap';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export default function KpiCard({ data, index }) {
  const cardRef = useRef(null);

  useEffect(() => {
    gsap.fromTo(
      cardRef.current,
      { y: 30, opacity: 0 },
      { y: 0, opacity: 1, duration: 0.5, delay: 0.08 * index, ease: 'power2.out' }
    );
  }, [index]);

  const maxVal = Math.max(...data.sparkline);
  const minVal = Math.min(...data.sparkline);
  const range = maxVal - minVal || 1;

  return (
    <div
      ref={cardRef}
      className="glass-card p-5 relative overflow-hidden group"
    >
      {/* Sparkline BG */}
      <div className="absolute inset-0 opacity-[0.04] pointer-events-none">
        <svg viewBox={`0 0 ${data.sparkline.length - 1} 100`} className="w-full h-full">
          <polyline
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="text-blue-400"
            points={data.sparkline
              .map((v, i) => `${i},${100 - ((v - minVal) / range) * 80 - 10}`)
              .join(' ')}
          />
        </svg>
      </div>

      <div className="relative">
        <p className="text-xs text-slate-500 font-medium">{data.title}</p>
        <div className="flex items-baseline gap-2 mt-1">
          <span className="text-2xl font-semibold text-slate-100">{data.value}</span>
          {data.change !== '–' && (
            <span
              className={`flex items-center gap-0.5 text-xs font-medium ${
                data.positive ? 'text-emerald-400' : 'text-red-400'
              }`}
            >
              {data.positive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
              {data.change}
            </span>
          )}
          {data.change === '–' && (
            <span className="flex items-center gap-0.5 text-xs text-slate-500">
              <Minus size={12} /> {data.change}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
