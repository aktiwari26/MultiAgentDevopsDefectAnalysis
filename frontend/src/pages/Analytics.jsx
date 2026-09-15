import { useRef, useEffect } from 'react';
import gsap from 'gsap';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';
import { BarChart3, TrendingUp } from 'lucide-react';
import { kpiData, issuesOverTime, logTypeDistribution, pipelineTimeByService } from '../data/mockData';
import KpiCard from '../components/KpiCard';
import IssuesTable from '../components/IssuesTable';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload) return null;
  return (
    <div className="glass rounded-xl px-4 py-3 shadow-xl border border-white/[0.08]">
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} className="text-xs font-medium" style={{ color: p.color }}>
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  );
};

export default function Analytics() {
  const headerRef = useRef(null);
  const kpiRef = useRef(null);
  const chartsRef = useRef(null);

  useEffect(() => {
    gsap.fromTo(headerRef.current, { y: 30, opacity: 0 }, { y: 0, opacity: 1, duration: 0.6, ease: 'power3.out' });
    gsap.fromTo(chartsRef.current, { y: 30, opacity: 0 }, { y: 0, opacity: 1, duration: 0.6, ease: 'power2.out', delay: 0.2 });
  }, []);

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div ref={headerRef}>
        <h1 className="text-2xl font-bold text-slate-100">Analytics</h1>
        <p className="text-sm text-slate-500 mt-1">Pipeline performance metrics and incident trends</p>
      </div>

      {/* KPI Grid */}
      <div ref={kpiRef} className="grid grid-cols-6 gap-4">
        {kpiData.map((kpi, i) => (
          <KpiCard key={kpi.title} data={kpi} index={i} />
        ))}
      </div>

      {/* Charts */}
      <div ref={chartsRef} className="grid grid-cols-2 gap-5">
        {/* Issues Over Time */}
        <div className="glass-card p-5 col-span-2 lg:col-span-1">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-200">Issues Over Time</h3>
              <p className="text-[11px] text-slate-500 mt-0.5">Monthly incident volume by severity</p>
            </div>
            <TrendingUp size={16} className="text-slate-500" />
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={issuesOverTime}>
              <defs>
                {['#ef4444', '#eab308', '#3b82f6'].map((color, i) => (
                  <linearGradient key={i} id={`gradient-${i}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={color} stopOpacity={0.2} />
                    <stop offset="95%" stopColor={color} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="critical" stroke="#ef4444" fill="url(#gradient-0)" strokeWidth={1.5} name="Critical" />
              <Area type="monotone" dataKey="warning" stroke="#eab308" fill="url(#gradient-1)" strokeWidth={1.5} name="Warning" />
              <Area type="monotone" dataKey="info" stroke="#3b82f6" fill="url(#gradient-2)" strokeWidth={1.5} name="Info" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Log Type Distribution */}
        <div className="glass-card p-5 col-span-2 lg:col-span-1">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-200">Log Type Distribution</h3>
              <p className="text-[11px] text-slate-500 mt-0.5">Volume by source category</p>
            </div>
            <BarChart3 size={16} className="text-slate-500" />
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={logTypeDistribution} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <YAxis dataKey="type" type="category" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={90} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={20}>
                {logTypeDistribution.map((_, i) => (
                  <rect key={i} fill={`url(#barGrad-${i % 3})`} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Pipeline Time by Service */}
        <div className="glass-card p-5 col-span-2">
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-slate-200">Pipeline Time by Service</h3>
            <p className="text-[11px] text-slate-500 mt-0.5">Average duration per agent (seconds)</p>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={pipelineTimeByService} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <YAxis dataKey="service" type="category" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={90} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="time" radius={[0, 4, 4, 0]} maxBarSize={18}>
                {pipelineTimeByService.map((_, i) => (
                  <rect key={i} fill={['#4f46e5', '#7c3aed', '#8b5cf6', '#6366f1', '#6d28d9', '#a78bfa', '#818cf8'][i % 7]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Table */}
      <IssuesTable />
    </div>
  );
}
