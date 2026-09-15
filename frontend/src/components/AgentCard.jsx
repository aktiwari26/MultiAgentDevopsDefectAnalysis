import { forwardRef } from 'react';
import { Tag, AlertTriangle, Search, Wrench, BookOpen, Ticket, Bell, Check, Loader2 } from 'lucide-react';

const iconMap = {
  Tag, AlertTriangle, Search, Wrench, BookOpen, Ticket, Bell,
};

const statusConfig = {
  pending: { border: 'border-white/[0.04]', text: 'text-slate-600', icon: 'text-slate-700' },
  processing: { border: 'border-blue-500/30', text: 'text-blue-300', icon: 'text-blue-400' },
  done: { border: 'border-emerald-500/30', text: 'text-emerald-300', icon: 'text-emerald-400' },
};

const AgentCard = forwardRef(({ agent, index, isActive }, ref) => {
  const Icon = iconMap[agent.icon] || Tag;
  const cfg = statusConfig[agent.status];
  const elapsed = (agent.time / 1000).toFixed(1);

  return (
    <div
      ref={ref}
      data-agent-id={agent.id}
      className={`relative flex flex-col items-center gap-3 p-5 rounded-2xl border transition-all duration-500 min-w-[110px] ${
        cfg.border
      } ${
        agent.status === 'processing'
          ? 'bg-blue-500/8 shadow-[0_0_25px_rgba(59,130,246,0.1)]'
          : agent.status === 'done'
          ? 'bg-emerald-500/8 shadow-[0_0_25px_rgba(52,211,153,0.08)]'
          : 'bg-white/[0.03]'
      } ${isActive ? 'scale-110' : ''}`}
    >
      {/* Icon */}
      <div className={`relative ${agent.status === 'done' ? cfg.icon : 'text-slate-400'}`}>
        {agent.status === 'processing' ? (
          <Loader2 size={24} className="animate-spin text-blue-400" />
        ) : agent.status === 'done' ? (
          <div className="w-[24px] h-[24px] rounded-full bg-emerald-500/20 flex items-center justify-center">
            <Check size={16} className="text-emerald-400" />
          </div>
        ) : (
          <Icon size={22} strokeWidth={1.5} />
        )}
      </div>

      {/* Label */}
      <span className={`text-[12px] font-bold tracking-tight leading-tight text-center ${cfg.text}`}>
        {agent.label}
      </span>



      {/* Time */}
      {agent.status === 'done' && (
        <span className="text-[10px] text-emerald-500/70 font-mono">{elapsed}s</span>
      )}

      {/* Progress bar */}
      {agent.status === 'processing' && (
        <div className="progress-bar w-full absolute bottom-2 left-3 right-3" style={{ width: 'calc(100% - 24px)' }}>
          <div
            className="progress-bar-fill"
            style={{
              width: `${Math.min((agent.time / 2000) * 100, 100)}%`,
            }}
          />
        </div>
      )}
    </div>
  );
});

AgentCard.displayName = 'AgentCard';
export default AgentCard;
