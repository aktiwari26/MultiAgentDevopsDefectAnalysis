import { useRef, useEffect } from 'react';
import gsap from 'gsap';
import { 
  Download, Terminal, Monitor, Apple, Layout, Shield, Cpu, 
  ArrowLeft, Brain, Zap, Database, GitBranch, Table, Layers, 
  CheckCircle2, AlertTriangle, Code2, Workflow, Globe, Rocket,
  ArrowRight, Info
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Docs() {
  const navigate = useNavigate();
  const containerRef = useRef(null);

  useEffect(() => {
    gsap.fromTo(containerRef.current, { opacity: 0 }, { opacity: 1, duration: 0.8 });
    
    const sections = document.querySelectorAll('section');
    sections.forEach((section, i) => {
      gsap.fromTo(section, 
        { opacity: 0, y: 30 }, 
        { opacity: 1, y: 0, duration: 0.6, delay: 0.1 * i, ease: 'power2.out' }
      );
    });
  }, []);

  const handlePrint = () => {
    window.print();
  };

  return (
    <div ref={containerRef} className="max-w-6xl mx-auto py-12 px-8 pb-32 space-y-24">
      {/* Background Elements */}
      <div className="fixed inset-0 pointer-events-none opacity-[0.02] overflow-hidden print:hidden">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-blue-500 blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-indigo-500 blur-[120px]" />
      </div>

      {/* Header */}
      <header className="relative space-y-6">
        <div className="flex items-center justify-between print:hidden">
          <div className="flex items-center gap-6">
            <button 
              onClick={() => navigate('/dashboard')}
              className="group flex items-center gap-2 text-slate-500 hover:text-blue-400 transition-all text-xs font-bold uppercase tracking-widest"
            >
              <div className="w-8 h-8 rounded-full border border-white/[0.06] flex items-center justify-center group-hover:border-blue-500/30 group-hover:bg-blue-500/5 transition-all">
                <ArrowLeft size={14} />
              </div>
              Dashboard
            </button>
            <div className="w-[1px] h-4 bg-white/[0.06]" />
            <div className="flex items-center gap-2">
              <img src="/logo_nobg.png" alt="DevOps Logo" className="w-6 h-6 object-contain" />
              <span className="text-[10px] font-black text-slate-100 uppercase tracking-widest">DevOps Docs</span>
            </div>
          </div>
          <button 
            onClick={handlePrint}
            className="flex items-center gap-2 px-6 py-3 rounded-xl bg-indigo-600/10 text-indigo-400 border border-indigo-500/20 hover:bg-indigo-600/20 transition-all font-semibold text-sm"
          >
            <Download size={16} /> Export Technical PDF
          </button>
        </div>


        <div className="pt-8">
          <div className="flex items-center gap-3 mb-4">
             <span className="px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 text-[10px] font-bold uppercase tracking-widest border border-blue-500/20">
              Technical Documentation
            </span>
            <span className="text-slate-700 text-xs">/</span>
            <span className="text-slate-500 text-[10px] font-bold uppercase tracking-widest">v1.0.0 Stable</span>
          </div>
          <h1 className="text-6xl font-black text-slate-100 tracking-tighter leading-tight print:text-slate-900">
            SYSTEM <span className="text-blue-500">ARCHITECTURE</span>
          </h1>
          <p className="text-xl text-slate-500 max-w-2xl mt-4 leading-relaxed print:text-slate-700">
            A comprehensive breakdown of the DevOps autonomous agent pipeline, state management, and deployment protocols.
          </p>
        </div>
      </header>

      {/* Pipeline Visualization Section */}
      <section className="space-y-12">
        <div className="flex items-center gap-3 text-emerald-400">
          <Workflow size={20} />
          <h2 className="text-xs font-bold uppercase tracking-[0.2em]">Agent Pipeline Logic</h2>
        </div>

        <div className="glass rounded-[3rem] p-12 border-white/[0.04] overflow-hidden relative group">
          {/* Animated Flow Track */}
          <div className="absolute inset-0 opacity-[0.02] pointer-events-none">
            <div className="absolute top-1/2 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-blue-500 to-transparent" />
          </div>

          <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-8 md:gap-4">
            
            {/* Stage 1: Ingestion */}
            <div className="flex flex-col items-center gap-4">
              <div className="relative">
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-[8px] font-black text-emerald-400 uppercase tracking-widest">Entry</div>
                <div className="w-32 h-32 rounded-3xl bg-emerald-500/5 border-2 border-emerald-500/20 flex flex-col items-center justify-center gap-2 group-hover:border-emerald-500/40 transition-all duration-500">
                  <Database size={28} className="text-emerald-400" />
                  <span className="text-xs font-bold text-slate-200 uppercase">Raw Logs</span>
                </div>
              </div>
            </div>

            <ArrowRight size={20} className="text-slate-700 hidden md:block" />

            {/* Stage 2: Triage */}
            <div className="flex flex-col gap-6">
              <div className="w-32 h-24 rounded-2xl bg-white/[0.03] border border-white/[0.08] flex flex-col items-center justify-center gap-2">
                <Layers size={20} className="text-blue-400" />
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Classifier</span>
              </div>
              <div className="w-32 h-24 rounded-2xl bg-white/[0.03] border border-white/[0.08] flex flex-col items-center justify-center gap-2">
                <AlertTriangle size={20} className="text-amber-400" />
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Severity</span>
              </div>
            </div>

            <ArrowRight size={20} className="text-slate-700 hidden md:block" />

            {/* Stage 3: Reasoning Router */}
            <div className="flex flex-col gap-8">
              {/* P1/P2 Branch */}
              <div className="p-6 rounded-3xl bg-blue-500/[0.02] border border-blue-500/10 space-y-4">
                <div className="text-[8px] font-black text-blue-400 uppercase tracking-[0.2em]">P1 / P2 Incidents</div>
                <div className="flex items-center gap-4">
                  <div className="w-28 h-24 rounded-2xl bg-white/[0.03] border border-white/[0.08] flex flex-col items-center justify-center gap-2 border-blue-500/30">
                    <Brain size={20} className="text-blue-400" />
                    <span className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">RCA Agent</span>
                  </div>
                  <ArrowRight size={14} className="text-slate-700" />
                  <div className="w-28 h-24 rounded-2xl bg-white/[0.03] border border-white/[0.08] flex flex-col items-center justify-center gap-2 border-blue-500/30">
                    <Zap size={20} className="text-blue-400" />
                    <span className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">Planner</span>
                  </div>
                </div>
              </div>
              
              {/* P3/P4 Branch */}
              <div className="p-6 rounded-3xl bg-slate-500/[0.02] border border-white/5 space-y-4">
                <div className="text-[8px] font-black text-slate-500 uppercase tracking-[0.2em]">P3 / P4 Incidents</div>
                <div className="w-full h-20 rounded-2xl bg-white/[0.02] border border-white/[0.06] flex flex-col items-center justify-center gap-2">
                  <GitBranch size={20} className="text-slate-500" />
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Cookbook</span>
                </div>
              </div>
            </div>

            <ArrowRight size={20} className="text-slate-700 hidden md:block" />

            {/* Stage 4: Operations */}
            <div className="relative">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded-full bg-violet-500/20 border border-violet-500/40 text-[8px] font-black text-violet-400 uppercase tracking-widest whitespace-nowrap">Parallel Ops</div>
              <div className="p-6 rounded-[2rem] bg-violet-500/[0.02] border border-violet-500/10 flex flex-col gap-4">
                <div className="w-32 h-24 rounded-2xl bg-white/[0.03] border border-white/[0.08] flex flex-col items-center justify-center gap-2 border-violet-500/30">
                  <Rocket size={20} className="text-violet-400" />
                  <span className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">JIRA Agent</span>
                </div>
                <div className="w-32 h-24 rounded-2xl bg-white/[0.03] border border-white/[0.08] flex flex-col items-center justify-center gap-2 border-violet-500/30">
                  <Globe size={20} className="text-violet-400" />
                  <span className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">Notification</span>
                </div>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* Technical Specifications Matrix */}
      <section className="space-y-10">
        <div className="flex items-center gap-3 text-blue-400">
          <Table size={20} />
          <h2 className="text-xs font-bold uppercase tracking-[0.2em]">Agent Matrix & Tiering</h2>
        </div>
        <div className="glass rounded-[2rem] overflow-hidden border-white/[0.04]">
           <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-white/[0.02] border-b border-white/[0.06]">
                <th className="px-8 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Service Unit</th>
                <th className="px-8 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Model Tier</th>
                <th className="px-8 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Logic Function</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {[
                { name: 'Classifier', model: 'GPT-4o-mini', role: 'Pattern Discovery & Ingestion Summary' },
                { name: 'Severity', model: 'GPT-4o-mini', role: 'Triage Routing (P1-P4) & Safety Filtering' },
                { name: 'RCA Analyst', model: 'GPT-4o', role: 'RAG-Grounded Context Retrieval (LanceDB)' },
                { name: 'Planner', model: 'GPT-4o', role: 'Deterministic Remediation Pathing' },
                { name: 'Cookbook', model: 'GPT-4o-mini', role: 'Runbook Generation & SOP Synthesis' }
              ].map((agent) => (
                <tr key={agent.name} className="border-b border-white/[0.02] hover:bg-white/[0.01] transition-colors">
                  <td className="px-8 py-6 font-bold text-slate-200">{agent.name}</td>
                  <td className="px-8 py-6 text-[10px] font-mono text-blue-400 uppercase tracking-wider">{agent.model}</td>
                  <td className="px-8 py-6 text-slate-400 leading-relaxed text-xs">{agent.role}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* State Schema Explorer */}
      <section className="space-y-10">
        <div className="flex items-center gap-3 text-rose-400">
          <Database size={20} />
          <h2 className="text-xs font-bold uppercase tracking-[0.2em]">State Schema Definition</h2>
        </div>
        <div className="glass rounded-[2.5rem] p-10 border-white/[0.04] grid grid-cols-1 md:grid-cols-2 gap-12">
          <div className="space-y-6">
            <h3 className="text-xl font-bold text-slate-200 tracking-tight">The DevOpsState</h3>
            <p className="text-sm text-slate-500 leading-relaxed">
              Orchestration is managed via an immutable TypedDict state. We utilize **LangGraph Reducers** to handle parallel data accumulation safely.
            </p>
            <div className="space-y-3">
              {[
                { label: 'raw_logs', type: 'str', desc: 'Original log stream input' },
                { label: 'severity', type: 'Enum[P1-P4]', desc: 'Incident priority level' },
                { label: 'jira_tickets', type: 'Annotated[list, add]', desc: 'Parallel ticket accumulator' }
              ].map((item) => (
                <div key={item.label} className="flex items-start gap-3">
                  <Info size={14} className="text-rose-500/50 mt-1" />
                  <div>
                    <span className="text-xs font-mono text-slate-300 font-bold">{item.label}</span>
                    <span className="text-[10px] text-slate-600 ml-2 italic">({item.type})</span>
                    <p className="text-[11px] text-slate-500 mt-0.5">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-black/20 rounded-3xl p-8 border border-white/[0.04] font-mono text-[11px] text-rose-400/80 print:text-slate-900 print:border-slate-300">
            <pre className="custom-scrollbar overflow-x-auto">{`class DevOpsState(TypedDict):
    raw_logs: str
    log_summary: str
    severity: str
    root_cause_analysis: str
    remediation_plan: str
    jira_tickets: Annotated[list, add]
    notifications: Annotated[list, add]`}</pre>
          </div>
        </div>
      </section>

      {/* Deployment Matrix */}
      <section className="space-y-10">
        <div className="flex items-center gap-3 text-amber-400">
          <Terminal size={20} />
          <h2 className="text-xs font-bold uppercase tracking-[0.2em]">Deployment Matrix</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { id: 'win', name: 'Windows', icon: Monitor, cmd: '.\\.venv\\Scripts\\activate' },
            { id: 'mac', name: 'macOS', icon: Apple, cmd: 'source .venv/bin/activate' },
            { id: 'linux', name: 'Linux', icon: Cpu, cmd: 'source .venv/bin/activate' }
          ].map((os) => (
            <div key={os.id} className="glass rounded-[2rem] p-8 border-white/[0.04] space-y-6">
              <div className="flex items-center gap-3">
                <os.icon size={20} className="text-slate-500" />
                <h3 className="font-bold text-slate-200">{os.name}</h3>
              </div>
              <code className="block text-[10px] bg-black/20 p-3 rounded-lg border border-white/[0.04] text-slate-400 font-mono">
                {os.cmd}
              </code>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="pt-20 border-t border-white/[0.06] text-center space-y-4">
        <p className="text-slate-600 text-xs font-mono uppercase tracking-[0.4em]">
          End of Specification • DevOps Autonomous Systems
        </p>
        <div className="hidden print:block text-slate-400 text-[10px]">
          © 2026 DevOps Engineering • Technical Whitepaper v1.0.0
        </div>
      </footer>

      <style dangerouslySetInnerHTML={{ __html: `
        @media print {
          body { background: white !important; color: black !important; }
          .glass { background: white !important; border: 1px solid #e2e8f0 !important; box-shadow: none !important; border-radius: 1rem !important; }
          h1, h2, h3, h4, p, span, div, pre, code { color: black !important; }
          .text-blue-500, .text-emerald-400, .text-amber-400, .text-rose-400, .text-violet-400 { color: black !important; border-color: #e2e8f0 !important; }
          pre, code { background: #f8fafc !important; border: 1px solid #e2e8f0 !important; }
          .print\\:hidden { display: none !important; }
          .print\\:block { display: block !important; }
          section { page-break-inside: avoid; margin-bottom: 3rem !important; }
        }
      `}} />
    </div>
  );
}
