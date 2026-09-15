import { useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import gsap from 'gsap';
import {
  Home,
  BarChart3,
  Sliders,
  ChevronDown,
  Activity,
  Server,
  Ticket,
  Bot,
  Globe,
  BookOpen,
} from 'lucide-react';

import { useStore } from '../store';

import CustomSelect from './CustomSelect';
import { AVAILABLE_MODELS } from '../data/tuningConfig';

const navItems = [
  { path: '/dashboard', label: 'Home', icon: Home },
  { path: '/dashboard/analytics', label: 'Analytics', icon: BarChart3 },
  { path: '/dashboard/rag', label: 'RAG Tuning', icon: Sliders },
  { path: '/dashboard/docs', label: 'Documentation', icon: BookOpen },
];


export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const {
    setActivePage, activePage, tuning, updateTuning, models,
    connections: dynamicConnections, fetchConnections,
    selectedProvider, setSelectedProvider, fetchModels,
    byokProvider, setByokProvider, byokKeys, setByokKey,
    byokStatus, checkByokConnection
  } = useStore();


  const byokOptions = [
    { id: 'openrouter', name: 'OpenRouter' },
    { id: 'ollama', name: 'Ollama (Local)' },
    { id: 'nvidia', name: 'Nvidia NIM' },
    { id: 'openai', name: 'OpenAI (Direct)' },
    { id: 'anthropic', name: 'Anthropic' },
    { id: 'google', name: 'Google AI' }
  ];


  const providers = [
    { id: 'all', name: 'All Providers' },
    ...[...new Set(models.map(m => m.provider))]
      .filter(Boolean)
      .sort()
      .map(p => ({
        id: p,
        name: p.charAt(0).toUpperCase() + p.slice(1)
      }))
  ];


  const fastModels = models
    .filter(m => m.category === 'fast' && (selectedProvider === 'all' || m.provider.toLowerCase() === selectedProvider.toLowerCase()));

  const reasoningModels = models
    .filter(m => m.category === 'reasoning' && (selectedProvider === 'all' || m.provider.toLowerCase() === selectedProvider.toLowerCase()));


  useEffect(() => {
    fetchConnections();
    fetchModels();
    const interval = setInterval(fetchConnections, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Make sure the current selections are valid for the selected provider
    const availableModels = (models.length > 0 ? models : AVAILABLE_MODELS.map(m => ({ id: m, provider: m.split('/')[0] })));

    const currentFast = availableModels.find(m => m.id === tuning.fast_model);
    const isFastValid = currentFast && (selectedProvider === 'all' || currentFast.provider.toLowerCase() === selectedProvider.toLowerCase());

    if (!isFastValid) {
      const firstAvailable = fastModels[0];
      if (firstAvailable) {
        updateTuning({ fast_model: firstAvailable.id });
      }
    }

    const currentReasoning = availableModels.find(m => m.id === tuning.reasoning_model);
    const isReasoningValid = currentReasoning && (selectedProvider === 'all' || currentReasoning.provider.toLowerCase() === selectedProvider.toLowerCase());

    if (!isReasoningValid) {
      const firstAvailable = reasoningModels[0];
      if (firstAvailable) {
        updateTuning({ reasoning_model: firstAvailable.id });
      }
    }
  }, [selectedProvider, models, fastModels, reasoningModels, tuning.fast_model, tuning.reasoning_model]);

  const sidebarRef = useRef(null);
  const itemsRef = useRef([]);

  useEffect(() => {
    gsap.fromTo(
      sidebarRef.current,
      { x: -280, opacity: 0 },
      { x: 0, opacity: 1, duration: 0.6, ease: 'power3.out' }
    );
    gsap.fromTo(
      itemsRef.current.filter(Boolean),
      { x: -20, opacity: 0 },
      { x: 0, opacity: 1, duration: 0.4, stagger: 0.06, ease: 'power2.out', delay: 0.2 }
    );
  }, []);

  const handleNav = (path, label) => {
    setActivePage(label.toLowerCase());
    navigate(path);
  };

  return (
    <aside
      ref={sidebarRef}
      className="fixed left-0 top-0 h-screen w-64 z-50 flex flex-col glass border-r border-white/[0.06]"
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 h-20 border-b border-white/[0.06] shrink-0">
        <div className="w-10 h-10 flex items-center justify-center relative group">
          <div className="absolute inset-0 bg-blue-500/20 blur-xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
          <img src="/logo_nobg.png" alt="DevOps Logo" className="w-full h-full object-contain relative z-10" />
        </div>
        <div>
          <span className="text-sm font-black text-slate-100 uppercase tracking-widest">DevOps</span>
          <span className="text-[10px] font-bold text-slate-500 block leading-none mt-0.5 uppercase tracking-tighter">AI Systems Hub</span>
        </div>
      </div>


      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <p className="px-2 text-[11px] font-semibold uppercase tracking-widest text-slate-500 mb-3">Navigation</p>
        {navItems.map((item, i) => {
          const isActive = location.pathname === item.path;
          const Icon = item.icon;
          return (
            <button
              key={item.path}
              ref={(el) => (itemsRef.current[i] = el)}
              onClick={() => handleNav(item.path, item.label)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${isActive
                ? 'bg-white/[0.08] text-slate-100 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                }`}
            >
              <Icon size={17} strokeWidth={1.5} />
              {item.label}
            </button>
          );
        })}

        {/* Configuration */}
        <div className="pt-5 mt-5 border-t border-white/[0.06]">
          <p className="px-2 text-[11px] font-semibold uppercase tracking-widest text-slate-500 mb-4">Configuration</p>

          <div className="px-2 space-y-4">
            <CustomSelect
              label="Provider"
              value={selectedProvider}
              options={providers.length > 1 ? providers : [{ id: 'none', name: 'No providers found' }]}
              onChange={(v) => setSelectedProvider(v)}
              icon={Globe}
            />
            <CustomSelect
              label="Fast Model"
              value={tuning.fast_model}
              options={fastModels.length > 0 ? fastModels : [{ id: 'none', name: 'Check Connection/Keys' }]}
              onChange={(v) => updateTuning({ fast_model: v })}
              icon={Server}
            />
            <CustomSelect
              label="Reasoning Model"
              value={tuning.reasoning_model}
              options={reasoningModels.length > 0 ? reasoningModels : [{ id: 'none', name: 'Check Connection/Keys' }]}
              onChange={(v) => updateTuning({ reasoning_model: v })}
              icon={Bot}
            />
          </div>
        </div>

        {/* Status Indicators */}
        <div className="pt-5 mt-5 border-t border-white/[0.06]">
          <p className="px-2 text-[11px] font-semibold uppercase tracking-widest text-slate-500 mb-3">Connections</p>
          <div className="space-y-2 px-2">
            {dynamicConnections.map((conn) => (
              <div key={conn.name} className="flex items-center justify-between">
                <span className="text-xs text-slate-400">{conn.name}</span>
                <span className={`pulse-dot ${conn.status} animate`} />
              </div>
            ))}
          </div>
        </div>
      </nav>

      {/* BYOK Section */}
      <div className="px-3 pb-4">
        <div className="glass-card p-3 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Connection Config</span>
            {byokKeys[byokProvider] && (
              <button
                onClick={() => setByokKey(byokProvider, '')}
                className="text-[9px] text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                Clear
              </button>
            )}
          </div>

          <div className="space-y-2">
            <select
              value={byokProvider}
              onChange={(e) => setByokProvider(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-[11px] text-slate-300 focus:outline-none focus:border-indigo-500/50 transition-all cursor-pointer"
            >
              {byokOptions.map(opt => (
                <option key={opt.id} value={opt.id} className="bg-slate-900">{opt.name}</option>
              ))}
            </select>

            <div className="relative">
              <input
                type={byokProvider === 'ollama' ? "text" : "password"}
                placeholder={byokProvider === 'ollama' ? "http://localhost:11434" : `Enter ${byokProvider} key`}
                value={byokKeys[byokProvider]}
                onChange={(e) => setByokKey(byokProvider, e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-[11px] text-slate-300 focus:outline-none focus:border-indigo-500/50 transition-all placeholder:text-slate-600"
              />
              <div
                className={`absolute right-2 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full transition-all duration-300 ${byokStatus === 'online' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' :
                  byokStatus === 'offline' ? 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]' :
                    byokStatus === 'checking' ? 'bg-amber-500 animate-pulse shadow-[0_0_8px_rgba(245,158,11,0.5)]' :
                      'bg-slate-600'
                  }`}
                title={`Status: ${byokStatus}`}
              />
            </div>
          </div>

          <p className="text-[9px] text-slate-500 leading-tight">
            {byokProvider === 'ollama'
              ? "Connecting to local LLM server. Ensure Ollama is running."
              : `Using custom ${byokProvider} key for secure agent orchestration.`}
          </p>
        </div>
      </div>
    </aside>
  );
}
