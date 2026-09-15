import { useRef, useEffect, useState } from 'react';
import gsap from 'gsap';
import { Download, ChevronDown, ChevronUp, Search } from 'lucide-react';
import { classifiedIssues } from '../data/mockData';

const severitySort = { Critical: 0, Error: 1, Warning: 2, Info: 3 };

export default function IssuesTable() {
  const tableRef = useRef(null);
  const [sortField, setSortField] = useState('date');
  const [sortDir, setSortDir] = useState('desc');
  const [search, setSearch] = useState('');

  useEffect(() => {
    gsap.fromTo(
      tableRef.current,
      { y: 30, opacity: 0 },
      { y: 0, opacity: 1, duration: 0.6, ease: 'power2.out', delay: 0.3 }
    );
  }, []);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const sorted = [...classifiedIssues]
    .filter(
      (r) =>
        r.title.toLowerCase().includes(search.toLowerCase()) ||
        r.id.toLowerCase().includes(search.toLowerCase())
    )
    .sort((a, b) => {
      let cmp = 0;
      if (sortField === 'severity') cmp = severitySort[a.severity] - severitySort[b.severity];
      else if (sortField === 'date') cmp = a.date.localeCompare(b.date);
      else if (sortField === 'id') cmp = a.id.localeCompare(b.id);
      else cmp = a[sortField]?.localeCompare(b[sortField]) || 0;
      return sortDir === 'asc' ? cmp : -cmp;
    });

  const SortIcon = ({ field }) => {
    if (sortField !== field) return <ChevronDown size={12} className="text-slate-600" />;
    return sortDir === 'asc' ? <ChevronUp size={12} className="text-blue-400" /> : <ChevronDown size={12} className="text-blue-400" />;
  };

  const statusDot = (status) => {
    const map = {
      Resolved: 'bg-emerald-400',
      Investigating: 'bg-amber-400',
      Open: 'bg-slate-500',
    };
    return <span className={`w-1.5 h-1.5 rounded-full ${map[status] || 'bg-slate-500'} inline-block`} />;
  };

  return (
    <div ref={tableRef} className="glass-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.06]">
        <h3 className="text-sm font-semibold text-slate-200">Classified Issues</h3>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search..."
              className="w-48 bg-white/[0.04] border border-white/[0.06] rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-300 placeholder:text-slate-600 focus:outline-none focus:border-blue-500/30"
            />
          </div>
          <button className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors px-3 py-1.5 rounded-lg hover:bg-white/[0.04]">
            <Download size={14} /> Export
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/[0.04]">
              {[
                { key: 'id', label: 'ID' },
                { key: 'title', label: 'Title' },
                { key: 'severity', label: 'Severity' },
                { key: 'status', label: 'Status' },
                { key: 'agent', label: 'Agent' },
                { key: 'time', label: 'Duration' },
                { key: 'date', label: 'Date' },
              ].map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className="text-left px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500 cursor-pointer hover:text-slate-300 transition-colors select-none"
                >
                  <div className="flex items-center gap-1">
                    {col.label}
                    <SortIcon field={col.key} />
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((issue, i) => (
              <tr
                key={issue.id}
                className="border-b border-white/[0.02] hover:bg-white/[0.02] transition-colors"
              >
                <td className="px-4 py-3 text-xs font-mono text-blue-400/80">{issue.id}</td>
                <td className="px-4 py-3 text-xs text-slate-300">{issue.title}</td>
                <td className="px-4 py-3">
                  <span
                    className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${
                      issue.severity === 'Critical'
                        ? 'text-red-400 bg-red-500/10'
                        : issue.severity === 'Error'
                        ? 'text-orange-400 bg-orange-500/10'
                        : issue.severity === 'Warning'
                        ? 'text-amber-400 bg-amber-500/10'
                        : 'text-blue-400 bg-blue-500/10'
                    }`}
                  >
                    {issue.severity}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1.5">
                    {statusDot(issue.status)}
                    <span className="text-xs text-slate-400">{issue.status}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-xs text-slate-500">{issue.agent}</td>
                <td className="px-4 py-3 text-xs font-mono text-slate-500">{issue.time}</td>
                <td className="px-4 py-3 text-xs text-slate-500">{issue.date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
