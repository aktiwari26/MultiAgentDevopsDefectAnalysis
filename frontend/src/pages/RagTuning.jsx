import { useRef, useEffect, useState } from 'react';
import gsap from 'gsap';
import { 
  Sliders, BookOpen, Code2, RotateCcw, ChevronRight, 
  Zap, Brain, FileText, Database, Settings, Terminal, 
  Save, Download, Play, Info, AlertTriangle, CheckCircle2
} from 'lucide-react';
import { useStore } from '../store';
import { ragPlaybooks } from '../data/mockData';
import { PRESETS, AVAILABLE_MODELS } from '../data/tuningConfig';

import CustomSelect from '../components/CustomSelect';

const playbookNames = Object.keys(ragPlaybooks);
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TRUNCATION_STRATEGIES = [
  "Head (first N chars)",
  "Tail (last N chars)",
  "Head + Tail",
];

const formatApiError = async (response) => {
  let message = `Request failed with status ${response.status}`;

  try {
    const data = await response.json();
    if (typeof data.detail === 'string') {
      message = data.detail;
    } else if (Array.isArray(data.detail)) {
      message = data.detail.map((err) => `${err.loc?.join('.') || 'field'}: ${err.msg}`).join('; ');
    }
  } catch {
    // Keep the HTTP status fallback if the response body is not JSON.
  }

  return message;
};

export default function RagTuning() {
  const { tuning, updateTuning, applyPreset, models, fetchModels, isLoadingModels } = useStore();
  const containerRef = useRef(null);
  const [selectedPlaybook, setSelectedPlaybook] = useState(playbookNames[0]);
  const [testLog, setTestLog] = useState("");
  const [testResult, setTestResult] = useState(null);
  const [isRunningTest, setIsRunningTest] = useState(false);

  useEffect(() => {
    fetchModels();
    const ctx = gsap.context(() => {
      gsap.from(".animate-in", {
        y: 20,
        opacity: 0,
        duration: 0.5,
        stagger: 0.1,
        ease: "power2.out"
      });
    }, containerRef);
    return () => ctx.revert();
  }, []);


  const handleRunTest = async () => {
    if (!testLog.trim()) return;
    setIsRunningTest(true);
    setTestResult(null);

    try {
      const validationResponse = await fetch(`${API_URL}/tuning/validate-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tuning),
      });

      if (!validationResponse.ok) {
        throw new Error(await formatApiError(validationResponse));
      }

      const runResponse = await fetch(`${API_URL}/tuning/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          log_text: testLog,
          config: tuning,
        }),
      });

      if (!runResponse.ok) {
        throw new Error(await formatApiError(runResponse));
      }

      const result = await runResponse.json();
      setTestResult({
        ...result,
        timestamp: new Date().toLocaleTimeString(),
      });
    } catch (error) {
      setTestResult({
        status: 'error',
        error: error.message || 'Failed to run tuning pipeline.',
        timestamp: new Date().toLocaleTimeString(),
      });
    } finally {
      setIsRunningTest(false);
    }
  };

  const handleExport = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(tuning, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", "devops_config.json");
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  };

  const ParamSlider = ({ label, value, min, max, step, onChange, unit = "", help = "" }) => (
    <div className="space-y-2 group">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <label className="text-[11px] text-slate-400 font-medium uppercase tracking-wider">{label}</label>
          {help && (
            <div className="relative group/help">
              <Info size={10} className="text-slate-600 hover:text-slate-400 cursor-help transition-colors" />
              <div className="absolute bottom-full left-0 mb-2 w-48 p-2 bg-slate-900 border border-white/10 rounded-lg text-[10px] text-slate-400 opacity-0 group-hover/help:opacity-100 pointer-events-none transition-opacity z-50 shadow-xl">
                {help}
              </div>
            </div>
          )}
        </div>
        <span className="text-[11px] font-mono text-indigo-400 tabular-nums bg-indigo-500/10 px-1.5 py-0.5 rounded border border-indigo-500/20">
          {typeof value === 'number' && !Number.isInteger(value) ? value.toFixed(2) : value}{unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-1 bg-white/5 rounded-full appearance-none cursor-pointer accent-indigo-500 hover:accent-indigo-400 transition-all
          [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3
          [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white
          [&::-webkit-slider-thumb]:shadow-[0_0_10px_rgba(255,255,255,0.4)]"
      />
    </div>
  );

  const ParamToggle = ({ label, value, onChange, help = "" }) => (
    <div className="flex items-center justify-between group">
      <div className="flex items-center gap-1.5">
        <label className="text-[11px] text-slate-400 font-medium uppercase tracking-wider">{label}</label>
        {help && (
          <div className="relative group/help">
            <Info size={10} className="text-slate-600 hover:text-slate-400 cursor-help transition-colors" />
            <div className="absolute bottom-full left-0 mb-2 w-48 p-2 bg-slate-900 border border-white/10 rounded-lg text-[10px] text-slate-400 opacity-0 group-hover/help:opacity-100 pointer-events-none transition-opacity z-50 shadow-xl">
              {help}
            </div>
          </div>
        )}
      </div>
      <button
        onClick={() => onChange(!value)}
        className={`w-8 h-4 rounded-full transition-all relative ${value ? 'bg-indigo-500' : 'bg-slate-700'}`}
      >
        <div className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-all ${value ? 'right-0.5' : 'left-0.5'}`} />
      </button>
    </div>
  );

  // Fallback models in case API fails
  const fastModels = models.length > 0 
    ? models.filter(m => m.category === 'fast') 
    : AVAILABLE_MODELS.filter(m => m.includes('mini') || m.includes('haiku') || m.includes('flash')).map(m => ({ id: m, name: m }));

  const reasoningModels = models.length > 0 
    ? models.filter(m => m.category === 'reasoning') 
    : AVAILABLE_MODELS.filter(m => !(m.includes('mini') || m.includes('haiku') || m.includes('flash'))).map(m => ({ id: m, name: m }));

  return (
    <div ref={containerRef} className="space-y-8 pb-16">
      {/* Header */}
      <div className="animate-in">
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Sliders className="text-indigo-400" size={24} />
          RAG & LLM Tuning Studio
        </h1>
        <p className="text-sm text-slate-400 mt-1">Fine-tune every parameter in the DevOps pipeline for maximum precision and performance</p>
      </div>

      {/* Presets Row */}
      <div className="animate-in glass-card p-4 flex flex-wrap items-center gap-4">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-widest mr-2">Quick Presets:</span>
        {Object.keys(PRESETS).map((name) => (
          <button
            key={name}
            onClick={() => applyPreset(PRESETS[name])}
            className="px-4 py-2 rounded-xl text-xs font-medium bg-white/5 border border-white/10 text-slate-300 hover:bg-white/10 hover:border-indigo-500/30 hover:text-indigo-300 transition-all"
          >
            {name}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          {isLoadingModels && (
            <div className="flex items-center gap-2 text-[10px] text-slate-500 bg-white/5 px-2 py-1 rounded-lg">
              <div className="w-2 h-2 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
              Updating Models...
            </div>
          )}
          <button 
            onClick={handleExport}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-[11px] font-semibold text-slate-400 hover:text-white hover:bg-white/5 transition-colors border border-transparent hover:border-white/10"
          >
            <Download size={14} /> Export JSON
          </button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Main Controls Panel */}
        <div className="col-span-12 lg:col-span-8 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* 1. Agent LLM Parameters */}
            <div className="animate-in glass-card p-6 space-y-6">
              <div className="flex items-center gap-2 border-b border-white/5 pb-4">
                <Brain size={18} className="text-purple-400" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">Agent LLM Parameters</h3>
              </div>
              
              <div className="space-y-8">
                {/* Fast Agent */}
                <div className="space-y-4 p-4 bg-white/[0.02] border border-white/5 rounded-xl">
                  <div className="flex items-center gap-2 mb-2">
                    <Zap size={14} className="text-amber-400" />
                    <span className="text-xs font-bold text-slate-300">Fast Agent (Classifier)</span>
                  </div>
                  <div className="space-y-4">
                    <CustomSelect 
                      label="Model Selection"
                      value={tuning.fast_model}
                      options={fastModels}
                      onChange={(v) => updateTuning({ fast_model: v })}
                      icon={Settings}
                    />
                    <ParamSlider 
                      label="Temperature" 
                      value={tuning.fast_temp} 
                      min={0} max={1} step={0.01}
                      onChange={(v) => updateTuning({ fast_temp: v })}
                      help="0 = deterministic, 1 = creative. Keep low for classification."
                    />
                    <ParamSlider 
                      label="Max Tokens" 
                      value={tuning.fast_max_tokens} 
                      min={128} max={2048} step={64}
                      onChange={(v) => updateTuning({ fast_max_tokens: v })}
                    />
                  </div>
                </div>

                {/* Reasoning Agent */}
                <div className="space-y-4 p-4 bg-white/[0.02] border border-white/5 rounded-xl">
                  <div className="flex items-center gap-2 mb-2">
                    <Brain size={14} className="text-purple-400" />
                    <span className="text-xs font-bold text-slate-300">Reasoning Agent (RCA)</span>
                  </div>
                  <div className="space-y-4">
                    <CustomSelect 
                      label="Model Selection"
                      value={tuning.reasoning_model}
                      options={reasoningModels}
                      onChange={(v) => updateTuning({ reasoning_model: v })}
                      icon={Brain}
                    />
                    <ParamSlider 
                      label="Temperature" 
                      value={tuning.reasoning_temp} 
                      min={0} max={1} step={0.01}
                      onChange={(v) => updateTuning({ reasoning_temp: v })}
                    />
                    <ParamSlider 
                      label="Max Tokens" 
                      value={tuning.reasoning_max_tokens} 
                      min={256} max={4096} step={64}
                      onChange={(v) => updateTuning({ reasoning_max_tokens: v })}
                    />
                  </div>
                </div>

                {/* Generation Agent */}
                <div className="space-y-4 p-4 bg-white/[0.02] border border-white/5 rounded-xl">
                  <div className="flex items-center gap-2 mb-2">
                    <FileText size={14} className="text-blue-400" />
                    <span className="text-xs font-bold text-slate-300">Generation Agent (Runbook)</span>
                  </div>
                  <div className="space-y-4">
                    <CustomSelect 
                      label="Model Selection"
                      value={tuning.generation_model}
                      options={reasoningModels}
                      onChange={(v) => updateTuning({ generation_model: v })}
                      icon={Code2}
                    />
                    <ParamSlider 
                      label="Temperature" 
                      value={tuning.generation_temp} 
                      min={0} max={1} step={0.01}
                      onChange={(v) => updateTuning({ generation_temp: v })}
                    />
                    <ParamSlider 
                      label="Max Tokens" 
                      value={tuning.generation_max_tokens} 
                      min={256} max={4096} step={64}
                      onChange={(v) => updateTuning({ generation_max_tokens: v })}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* 2. RAG & Knowledge Base */}
            <div className="animate-in glass-card p-6 space-y-6">
              <div className="flex items-center gap-2 border-b border-white/5 pb-4">
                <Database size={18} className="text-blue-400" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">RAG & Knowledge Base</h3>
              </div>

              <div className="space-y-6">
                <ParamSlider 
                  label="Top-K Results" 
                  value={tuning.rag_top_k} 
                  min={1} max={15} step={1}
                  onChange={(v) => updateTuning({ rag_top_k: v })}
                  help="Number of KB chunks retrieved per query. Higher = more context."
                />
                <ParamSlider 
                  label="Similarity Threshold" 
                  value={tuning.rag_similarity_threshold} 
                  min={0} max={1} step={0.01}
                  onChange={(v) => updateTuning({ rag_similarity_threshold: v })}
                  help="Minimum cosine similarity to include a chunk."
                />
                <div className="space-y-2">
                  <label className="text-[11px] text-slate-400 font-medium uppercase tracking-wider block">Chunk Size (Tokens)</label>
                  <div className="grid grid-cols-4 gap-2">
                    {[256, 512, 768, 1024].map(size => (
                      <button
                        key={size}
                        onClick={() => updateTuning({ rag_chunk_size: size })}
                        className={`py-1.5 rounded-lg text-[10px] font-mono border transition-all ${
                          tuning.rag_chunk_size === size 
                            ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-300' 
                            : 'bg-white/5 border-white/10 text-slate-500 hover:border-white/20'
                        }`}
                      >
                        {size}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="pt-4 border-t border-white/5">
                  <ParamToggle 
                    label="Keyword Fallback" 
                    value={tuning.kb_fallback} 
                    onChange={(v) => updateTuning({ kb_fallback: v })}
                    help="Falls back to keyword matching if vector search fails."
                  />
                </div>
              </div>

              <div className="mt-8 space-y-6 pt-6 border-t border-white/5">
                <div className="flex items-center gap-2 mb-2">
                  <FileText size={16} className="text-emerald-400" />
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">Log Processing</h3>
                </div>
                <ParamSlider 
                  label="Max Log Characters" 
                  value={tuning.max_log_chars} 
                  min={500} max={20000} step={500}
                  onChange={(v) => updateTuning({ max_log_chars: v })}
                  help="Truncates the raw log before sending to LLM."
                />
                <div>
                  <label className="text-[11px] text-slate-400 font-medium uppercase tracking-wider block mb-3">Truncation Strategy</label>
                  <div className="space-y-2">
                    {TRUNCATION_STRATEGIES.map(strategy => (
                      <button
                        key={strategy}
                        onClick={() => updateTuning({ truncation_strategy: strategy })}
                        className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-[11px] border transition-all ${
                          tuning.truncation_strategy === strategy 
                            ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-300' 
                            : 'bg-white/5 border-white/10 text-slate-500 hover:border-white/20'
                        }`}
                      >
                        {strategy}
                        {tuning.truncation_strategy === strategy && <CheckCircle2 size={12} className="text-indigo-400" />}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="space-y-3 pt-4 border-t border-white/5">
                  <ParamToggle label="Strip Timestamps" value={tuning.strip_timestamps} onChange={(v) => updateTuning({ strip_timestamps: v })} />
                  <ParamToggle label="Deduplicate Lines" value={tuning.deduplicate_lines} onChange={(v) => updateTuning({ deduplicate_lines: v })} />
                </div>
              </div>
            </div>
          </div>

          {/* 3. Live Test Runner */}
          <div className="animate-in glass-card p-6 space-y-6">
            <div className="flex items-center justify-between border-b border-white/5 pb-4">
              <div className="flex items-center gap-2">
                <Terminal size={18} className="text-emerald-400" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">Live Test Runner</h3>
              </div>
              <button
                onClick={handleRunTest}
                disabled={isRunningTest || !testLog.trim()}
                className={`flex items-center gap-2 px-6 py-2 rounded-xl text-xs font-bold transition-all ${
                  isRunningTest || !testLog.trim() 
                    ? 'bg-slate-800 text-slate-600 cursor-not-allowed' 
                    : 'bg-indigo-500 text-white shadow-[0_0_20px_rgba(99,102,241,0.4)] hover:bg-indigo-400 active:scale-95'
                }`}
              >
                {isRunningTest ? (
                  <>
                    <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Running...
                  </>
                ) : (
                  <>
                    <Play size={14} fill="currentColor" />
                    Run Test with Current Config
                  </>
                )}
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <label className="text-[11px] text-slate-500 font-bold uppercase tracking-wider">Input Log Snippet</label>
                  <button 
                    onClick={() => setTestLog("May 10 03:45:08 worker-node-01 kubelet[1245]: ERROR: failed to garbage collect container 'api-service-7f55': context deadline exceeded\nMay 10 03:45:10 worker-node-01 kubelet[1245]: WARNING: node 'worker-node-01' is under memory pressure")}
                    className="text-[10px] text-indigo-400 hover:text-indigo-300 underline"
                  >
                    Load Sample
                  </button>
                </div>
                <textarea
                  value={testLog}
                  onChange={(e) => setTestLog(e.target.value)}
                  placeholder="Paste a log snippet here..."
                  className="w-full h-48 bg-slate-950 border border-white/10 rounded-xl p-4 text-[13px] font-mono text-slate-300 focus:outline-none focus:border-emerald-500/30 transition-all resize-none"
                />
              </div>

              <div className="space-y-4">
                <label className="text-[11px] text-slate-500 font-bold uppercase tracking-wider block">Live Results</label>
                {testResult ? (
                  <div className={`h-48 bg-slate-950 border rounded-xl p-5 flex flex-col gap-4 overflow-auto animate-in ${
                    testResult.status === 'error' ? 'border-red-500/30' : 'border-white/10'
                  }`}>
                    {testResult.status === 'error' ? (
                      <>
                        <div className="bg-red-500/10 p-3 rounded-lg border border-red-500/20 flex items-start gap-3">
                          <AlertTriangle size={18} className="text-red-400 shrink-0 mt-0.5" />
                          <div>
                            <span className="text-[10px] text-red-300 uppercase block mb-1">Pipeline Error</span>
                            <p className="text-xs text-slate-300 leading-relaxed">{testResult.error}</p>
                          </div>
                        </div>
                        <span className="text-[10px] text-slate-600 font-mono">Last attempt: {testResult.timestamp}</span>
                      </>
                    ) : (
                      <>
                        <div className="grid grid-cols-2 gap-3">
                          <div className="bg-white/5 p-3 rounded-lg border border-white/5">
                            <span className="text-[10px] text-slate-500 uppercase block mb-1">Log Type</span>
                            <span className="text-sm font-bold text-white capitalize">{testResult.log_type || 'Unknown'}</span>
                          </div>
                          <div className="bg-white/5 p-3 rounded-lg border border-white/5">
                            <span className="text-[10px] text-slate-500 uppercase block mb-1">KB Hits</span>
                            <span className="text-sm font-bold text-white">{testResult.kb_hits ?? 0}</span>
                          </div>
                        </div>
                        <div className="bg-white/5 p-3 rounded-lg border border-white/5 flex items-center justify-between">
                          <div>
                            <span className="text-[10px] text-slate-500 uppercase block mb-1">Severity Detection</span>
                            <span className="text-xs font-bold text-amber-400">{testResult.severity || 'Pending'}</span>
                          </div>
                          <AlertTriangle size={18} className="text-amber-500/50" />
                        </div>
                        <p className="text-[11px] text-slate-400 leading-relaxed italic">
                          &quot;{testResult.summary || testResult.root_cause_analysis || 'Pipeline completed.'}&quot;
                        </p>
                      </>
                    )}
                  </div>
                ) : (
                  <div className="h-48 bg-slate-950/50 border border-white/[0.03] border-dashed rounded-xl flex flex-col items-center justify-center text-slate-700 text-center p-6">
                    <Terminal size={32} className="mb-3 opacity-20" />
                    <p className="text-[11px] uppercase tracking-widest font-medium">Wait for execution</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar Panel */}
        <div className="col-span-12 lg:col-span-4 space-y-6">
          
          {/* Config JSON View */}
          <div className="animate-in glass-card p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-4">
              <div className="flex items-center gap-2">
                <Code2 size={16} className="text-slate-400" />
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">Current Config JSON</h3>
              </div>
              <button 
                className="p-1.5 hover:bg-white/5 rounded-lg text-slate-500 hover:text-white transition-all"
                title="Save Custom Preset"
              >
                <Save size={14} />
              </button>
            </div>
            <div className="bg-slate-950/50 rounded-xl p-4 overflow-auto max-h-[300px] border border-white/5">
              <pre className="text-[10px] font-mono text-indigo-300 leading-relaxed">
                {JSON.stringify(tuning, null, 2)}
              </pre>
            </div>
          </div>

          {/* Playbook Selector & Viewer */}
          <div className="animate-in glass-card p-6 space-y-4">
            <div className="flex items-center gap-2 border-b border-white/5 pb-4">
              <BookOpen size={16} className="text-slate-400" />
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">Remediation Playbooks</h3>
            </div>
            <div className="space-y-2">
              {playbookNames.map((name) => (
                <button
                  key={name}
                  onClick={() => setSelectedPlaybook(name)}
                  className={`w-full flex items-center justify-between px-4 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 text-left ${
                    selectedPlaybook === name
                      ? 'bg-indigo-500/10 text-indigo-300 border border-indigo-500/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04] border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-1.5 h-1.5 rounded-full ${selectedPlaybook === name ? 'bg-indigo-400 animate-pulse' : 'bg-slate-700'}`} />
                    {name}
                  </div>
                  <ChevronRight size={14} className={selectedPlaybook === name ? 'text-indigo-400' : 'text-slate-700'} />
                </button>
              ))}
            </div>
            
            <div className="mt-6 pt-6 border-t border-white/5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-mono text-slate-500">remediation/{selectedPlaybook.toLowerCase().replace(/\s+/g, '_')}.yaml</span>
              </div>
              <div className="bg-slate-950 p-4 rounded-xl border border-white/5 overflow-auto max-h-[300px]">
                <pre className="text-[11px] leading-relaxed font-mono">
                  {ragPlaybooks[selectedPlaybook].split('\n').map((line, i) => {
                    const indent = line.search(/\S|$/);
                    const trimmed = line.trim();
                    let color = 'text-slate-400';
                    if (trimmed.startsWith('on_') || trimmed.endsWith(':')) color = 'text-blue-400';
                    else if (trimmed.startsWith('  ')) {
                      if (trimmed.includes(':')) color = 'text-indigo-400';
                      else if (trimmed.startsWith('- ')) color = 'text-slate-300';
                    }
                    if (trimmed.startsWith('#')) color = 'text-slate-600';
                    if (trimmed.startsWith('"') || trimmed.startsWith("'")) color = 'text-emerald-400';
                    if (trimmed.includes('${')) color = 'text-amber-400 font-bold';

                    return (
                      <div key={i} className="whitespace-pre" style={{ paddingLeft: indent * 4 }}>
                        <span className={color}>{line.trimStart()}</span>
                      </div>
                    );
                  })}
                </pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
