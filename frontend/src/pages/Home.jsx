import { useRef, useEffect, useState } from 'react';
import gsap from 'gsap';
import {
  Upload, FileText, Terminal, Brain, ArrowRight, Activity, AlertTriangle,
  Bell, BookOpen, CheckCircle2, Database, Gauge, Ticket, Wrench
} from 'lucide-react';

import { useStore } from '../store';
import { sampleLogs, severityColors } from '../data/mockData';
import PipelineProgress from '../components/PipelineProgress';

const getDefaultStreamUrl = () => {
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  try {
    const url = new URL(apiUrl);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    url.pathname = '/ws/logs';
    url.search = '';
    url.hash = '';
    return url.toString();
  } catch {
    return 'ws://localhost:8000/ws/logs';
  }
};

const normalizeWebSocketUrl = (value) => {
  const trimmed = value.trim();
  const url = new URL(trimmed);

  if (url.protocol === 'http:') {
    url.protocol = 'ws:';
  } else if (url.protocol === 'https:') {
    url.protocol = 'wss:';
  }

  if (!['ws:', 'wss:'].includes(url.protocol)) {
    throw new Error('Use a ws:// or wss:// URL.');
  }

  return url.toString();
};

const severityStyles = {
  P1: 'border-rose-500/30 bg-rose-500/10 text-rose-300',
  P2: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
  P3: 'border-blue-500/30 bg-blue-500/10 text-blue-300',
  P4: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
};

const ResultCard = ({ icon: Icon, title, children, className = '' }) => (
  <section className={`glass rounded-2xl border border-white/[0.08] overflow-hidden ${className}`}>
    <div className="flex items-center gap-2 px-5 py-3 border-b border-white/[0.06]">
      <Icon size={16} className="text-blue-400" />
      <h3 className="text-xs font-bold text-slate-300 uppercase tracking-widest">{title}</h3>
    </div>
    <div className="p-5">{children}</div>
  </section>
);

const MarkdownText = ({ text }) => {
  if (!text) {
    return <p className="text-sm text-slate-500">No details returned.</p>;
  }

  return (
    <div className="space-y-2 text-sm leading-6 text-slate-300">
      {text.split('\n').map((line, index) => {
        const trimmed = line.trim();

        if (!trimmed) {
          return <div key={index} className="h-2" />;
        }

        if (trimmed.startsWith('### ')) {
          return <h4 key={index} className="pt-3 text-base font-bold text-white">{trimmed.replace(/^###\s+/, '')}</h4>;
        }

        if (trimmed.startsWith('#### ')) {
          return <h5 key={index} className="pt-2 text-sm font-semibold text-blue-300">{trimmed.replace(/^####\s+/, '')}</h5>;
        }

        if (trimmed.startsWith('- [ ]')) {
          return (
            <div key={index} className="flex gap-2 text-slate-300">
              <span className="mt-2 h-3 w-3 shrink-0 rounded border border-slate-600" />
              <span>{trimmed.replace(/^- \[ \]\s*/, '')}</span>
            </div>
          );
        }

        if (trimmed.startsWith('- ') || /^\d+\.\s/.test(trimmed)) {
          return (
            <div key={index} className="flex gap-2 text-slate-300">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-400/70" />
              <span>{trimmed.replace(/^-\s*/, '')}</span>
            </div>
          );
        }

        if (trimmed.startsWith('```')) {
          return null;
        }

        return <p key={index}>{trimmed.replace(/\*\*/g, '')}</p>;
      })}
    </div>
  );
};

const ApiResultReport = ({ result }) => {
  const severity = result.severity || 'Unknown';
  const pipelineEntries = Object.entries(result.pipeline_status || {});

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="glass rounded-xl border border-white/[0.08] p-4">
          <span className="text-[10px] text-slate-500 uppercase tracking-widest">Severity</span>
          <div className={`mt-2 inline-flex px-3 py-1 rounded-full border text-sm font-bold ${severityStyles[severity] || 'border-slate-500/30 bg-slate-500/10 text-slate-300'}`}>
            {severity}
          </div>
        </div>
        <div className="glass rounded-xl border border-white/[0.08] p-4">
          <span className="text-[10px] text-slate-500 uppercase tracking-widest">Log Type</span>
          <p className="mt-2 text-sm font-semibold text-white capitalize">{result.log_type || 'Unknown'}</p>
        </div>
        <div className="glass rounded-xl border border-white/[0.08] p-4">
          <span className="text-[10px] text-slate-500 uppercase tracking-widest">JIRA</span>
          <p className="mt-2 text-sm font-semibold text-white">{result.jira_tickets?.length || 0} ticket{result.jira_tickets?.length === 1 ? '' : 's'}</p>
        </div>
        <div className="glass rounded-xl border border-white/[0.08] p-4">
          <span className="text-[10px] text-slate-500 uppercase tracking-widest">Notifications</span>
          <p className="mt-2 text-sm font-semibold text-white">{result.notifications_sent?.length || 0} sent</p>
        </div>
      </div>

      <ResultCard icon={Brain} title="Incident Summary">
        <MarkdownText text={result.log_summary} />
      </ResultCard>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <ResultCard icon={AlertTriangle} title="Critical Issues">
          <div className="space-y-3">
            {(result.critical_issues || []).map((issue, index) => (
              <div key={`${issue.title}-${index}`} className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-4">
                <div className="flex items-center justify-between gap-3 mb-2">
                  <span className="text-[10px] text-slate-500 uppercase tracking-widest">Issue {index + 1}</span>
                  <span className={`px-2 py-0.5 rounded-full border text-[10px] font-bold ${severityStyles[issue.severity] || severityStyles.P2}`}>
                    {issue.severity}
                  </span>
                </div>
                <p className="text-sm text-slate-200 leading-6">{issue.title}</p>
              </div>
            ))}
            {(!result.critical_issues || result.critical_issues.length === 0) && (
              <p className="text-sm text-slate-500">No critical issues returned.</p>
            )}
          </div>
        </ResultCard>

        <ResultCard icon={Gauge} title="Pipeline Status">
          <div className="space-y-2">
            {pipelineEntries.map(([agent, value]) => (
              <div key={agent} className="flex items-center justify-between rounded-lg bg-white/[0.03] px-3 py-2">
                <div className="flex items-center gap-2">
                  <CheckCircle2 size={14} className="text-emerald-400" />
                  <span className="text-sm text-slate-300 capitalize">{agent.replace(/_/g, ' ')}</span>
                </div>
                <span className="text-xs font-mono text-slate-500">{value.elapsed_s ?? '-'}s</span>
              </div>
            ))}
          </div>
        </ResultCard>
      </div>

      <ResultCard icon={Wrench} title="Root Cause">
        <MarkdownText text={result.root_cause_analysis} />
      </ResultCard>

      <ResultCard icon={Wrench} title="Remediation Plan">
        <MarkdownText text={result.remediation_plan} />
      </ResultCard>

      <ResultCard icon={BookOpen} title="Runbook">
        <MarkdownText text={result.cookbook} />
      </ResultCard>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <ResultCard icon={Ticket} title="JIRA Tickets">
          <div className="space-y-3">
            {(result.jira_tickets || []).map((ticket) => (
              <a
                key={ticket.key}
                href={ticket.url}
                target="_blank"
                rel="noreferrer"
                className="block rounded-xl border border-white/[0.08] bg-white/[0.03] p-4 hover:border-blue-500/30 hover:bg-blue-500/[0.04] transition-all"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-bold text-blue-300">{ticket.key}</span>
                  <span className="text-[10px] uppercase tracking-widest text-emerald-300">{ticket.mode || ticket.status}</span>
                </div>
                <p className="mt-2 text-sm text-slate-300">{ticket.summary}</p>
                <p className="mt-2 text-xs text-slate-500">{ticket.epic} · {ticket.sprint}</p>
              </a>
            ))}
            {(!result.jira_tickets || result.jira_tickets.length === 0) && (
              <p className="text-sm text-slate-500">No JIRA tickets returned.</p>
            )}
          </div>
        </ResultCard>

        <ResultCard icon={Bell} title="Notifications">
          <div className="space-y-3">
            {(result.notifications_sent || []).map((notification, index) => (
              <div key={`${notification.channel}-${index}`} className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-4">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-semibold text-slate-200">{notification.channel}</span>
                  <span className="text-xs text-emerald-300">{notification.status}</span>
                </div>
                {notification.http_status && (
                  <p className="mt-2 text-xs text-slate-500">HTTP {notification.http_status}</p>
                )}
              </div>
            ))}
            {(!result.notifications_sent || result.notifications_sent.length === 0) && (
              <p className="text-sm text-slate-500">No notifications returned.</p>
            )}
          </div>
        </ResultCard>
      </div>

      <ResultCard icon={Database} title="RAG Context">
        <div className="space-y-3">
          {(result.rag_context || []).map((context, index) => (
            <div key={index} className="rounded-xl border border-white/[0.08] bg-black/20 p-4 text-xs leading-5 text-slate-400 whitespace-pre-wrap">
              {context}
            </div>
          ))}
          {(!result.rag_context || result.rag_context.length === 0) && (
            <p className="text-sm text-slate-500">No RAG context returned.</p>
          )}
        </div>
      </ResultCard>
    </div>
  );
};

export default function Home() {
  const { 
    activeTab, setActiveTab, selectedSample, setSelectedSample, 
    logContent, setLogContent, startPipeline, pipelineStatus,
    liveLogs, addLiveLog, clearLiveLogs, analysisResult
  } = useStore();

  const heroRef = useRef(null);
  const subtitleRef = useRef(null);
  const inputAreaRef = useRef(null);
  const pipelineRef = useRef(null);
  const socketRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);
  const [liveStreamUrl, setLiveStreamUrl] = useState(getDefaultStreamUrl);
  const [liveStreamStatus, setLiveStreamStatus] = useState('idle');
  const [liveStreamError, setLiveStreamError] = useState('');

  const isListening = liveStreamStatus === 'connecting' || liveStreamStatus === 'connected';

  const stopListening = (resetStatus = true) => {
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    if (resetStatus) {
      setLiveStreamStatus('idle');
    }
  };

  const startListening = () => {
    let url;

    try {
      url = normalizeWebSocketUrl(liveStreamUrl);
    } catch (error) {
      setLiveStreamError(error.message || 'Enter a valid websocket URL.');
      setLiveStreamStatus('idle');
      return;
    }

    stopListening();
    setLiveStreamUrl(url);
    setLiveStreamError('');
    setLiveStreamStatus('connecting');

    const socket = new WebSocket(url);
    socketRef.current = socket;

    socket.onopen = () => {
      setLiveStreamStatus('connected');
    };

    socket.onmessage = (event) => {
      try {
        addLiveLog(JSON.parse(event.data));
      } catch {
        addLiveLog({
          id: crypto.randomUUID?.() || `live-${Date.now()}-${Math.random()}`,
          timestamp: new Date().toISOString(),
          content: event.data,
        });
      }
    };

    socket.onerror = () => {
      setLiveStreamError('Could not connect to the websocket stream.');
    };

    socket.onclose = () => {
      if (socketRef.current === socket) {
        socketRef.current = null;
        setLiveStreamStatus('idle');
      }
    };
  };

  useEffect(() => {
    if (activeTab !== 'live') {
      stopListening();
    }
  }, [activeTab]);

  useEffect(() => () => stopListening(false), []);

  useEffect(() => {
    gsap.fromTo(heroRef.current, { y: 40, opacity: 0 }, { y: 0, opacity: 1, duration: 0.7, ease: 'power3.out' });
    gsap.fromTo(subtitleRef.current, { y: 20, opacity: 0 }, { y: 0, opacity: 1, duration: 0.5, ease: 'power2.out', delay: 0.2 });
    gsap.fromTo(inputAreaRef.current, { y: 30, opacity: 0 }, { y: 0, opacity: 1, duration: 0.6, ease: 'power2.out', delay: 0.35 });
    gsap.fromTo(pipelineRef.current, { y: 40, opacity: 0 }, { y: 0, opacity: 1, duration: 0.6, ease: 'power2.out', delay: 0.5 });
  }, []);

  const handleDragOver = (e) => { e.preventDefault(); setDragOver(true); };
  const handleDragLeave = () => setDragOver(false);
  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => setLogContent(reader.result);
      reader.readAsText(file);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-10 pb-16">
      {/* Hero */}
      <div ref={heroRef} className="text-center pt-2">
        <h1 className="text-5xl font-extrabold tracking-tight text-balance leading-[1.1]">
          Observability.{' '}
          <span className="gradient-text">Triage.</span>{' '}
          <span className="gradient-text">Automate.</span>
        </h1>
        <p ref={subtitleRef} className="mt-4 text-base text-slate-500 max-w-xl mx-auto leading-relaxed">
          Let AI agents classify, diagnose, and resolve infrastructure incidents in seconds — not hours.
        </p>
      </div>

      {/* Input Area */}
      <div ref={inputAreaRef}>
        {/* Tabs */}
        <div className="flex gap-1 p-1 glass rounded-xl w-fit mx-auto mb-6">
          {[
            { id: 'log', label: 'Log Input', icon: Terminal },
            { id: 'live', label: 'Live Stream', icon: Activity },
            { id: 'sample', label: 'Sample Logs', icon: FileText },
          ].map((tab) => {
            const Icon = tab.icon || Terminal;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-white/[0.08] text-slate-200 shadow-sm'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                <Icon size={16} strokeWidth={1.5} />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        <div className="glass rounded-2xl p-6 min-h-[340px]">
          {activeTab === 'log' ? (
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200 ${
                dragOver
                  ? 'border-blue-500/50 bg-blue-500/5'
                  : 'border-white/[0.08] hover:border-white/[0.12]'
              }`}
            >
              <input
                type="file"
                id="log-upload"
                className="hidden"
                accept=".log,.txt,.json"
                onChange={(e) => {
                  const file = e.target.files[0];
                  if (file) {
                    const reader = new FileReader();
                    reader.onload = () => setLogContent(reader.result);
                    reader.readAsText(file);
                  }
                }}
              />
              <Upload size={32} className="mx-auto text-slate-600 mb-3" />
              <p className="text-sm text-slate-400 mb-1">
                Drop a log file here, or{' '}
                <label 
                  htmlFor="log-upload" 
                  className="text-blue-400 hover:text-blue-300 cursor-pointer underline underline-offset-4 decoration-blue-400/30 hover:decoration-blue-300 transition-all font-medium"
                >
                  browse
                </label>
              </p>
              <p className="text-xs text-slate-600">Supports .log, .txt, .json (max 10MB)</p>
              <textarea
                value={logContent}
                onChange={(e) => setLogContent(e.target.value)}
                placeholder="Or paste your log content here..."
                rows={5}
                className="mt-4 w-full bg-white/[0.03] border border-white/[0.06] rounded-lg px-4 py-3 text-sm text-slate-300 font-mono placeholder:text-slate-600 focus:outline-none focus:border-blue-500/30 resize-none"
              />
              {logContent && (
                <div className="mt-3 flex items-center justify-center gap-2 text-xs text-emerald-400">
                  <ArrowRight size={12} />
                  <span>{logContent.split('\n').length} lines loaded</span>
                </div>
              )}
            </div>
          ) : activeTab === 'live' ? (
            <div className="flex flex-col h-[300px]">
              <div className="flex flex-col gap-3 mb-4 px-2">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${
                      liveStreamStatus === 'connected'
                        ? 'bg-emerald-500 animate-pulse'
                        : liveStreamStatus === 'connecting'
                          ? 'bg-amber-500 animate-pulse'
                          : 'bg-slate-600'
                    }`} />
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest">
                      {liveStreamStatus === 'connected'
                        ? 'Listening'
                        : liveStreamStatus === 'connecting'
                          ? 'Connecting'
                          : 'Real-time Feed'}
                    </span>
                  </div>
                  <button 
                    onClick={clearLiveLogs}
                    className="text-[10px] font-bold text-slate-500 hover:text-slate-300 uppercase tracking-widest transition-colors self-start md:self-auto"
                  >
                    Clear Feed
                  </button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-2">
                  <input
                    type="url"
                    value={liveStreamUrl}
                    onChange={(e) => setLiveStreamUrl(e.target.value)}
                    disabled={isListening}
                    placeholder="ws://localhost:8000/ws/logs"
                    className="min-w-0 bg-white/[0.03] border border-white/[0.08] rounded-lg px-3 py-2 text-xs text-slate-300 font-mono placeholder:text-slate-600 focus:outline-none focus:border-blue-500/30 disabled:opacity-60"
                  />
                  <button
                    onClick={isListening ? () => stopListening() : startListening}
                    className={`px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-widest transition-all ${
                      isListening
                        ? 'bg-rose-500/10 text-rose-300 border border-rose-500/20 hover:bg-rose-500/20'
                        : 'bg-blue-500/10 text-blue-300 border border-blue-500/20 hover:bg-blue-500/20'
                    }`}
                  >
                    {isListening ? 'Stop' : 'Listen'}
                  </button>
                </div>
                {liveStreamError && (
                  <p className="text-[11px] text-rose-300">{liveStreamError}</p>
                )}
              </div>
              <div className="flex-1 bg-black/40 rounded-xl border border-white/[0.06] overflow-y-auto p-4 font-mono text-[11px] space-y-1 custom-scrollbar">
                {liveLogs.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-slate-600 italic">
                    {isListening ? 'Waiting for logs from websocket...' : 'Enter a websocket URL and click Listen.'}
                  </div>
                ) : (
                  liveLogs.map((log) => {
                    const isError = log.content.includes('ERROR');
                    const isWarn = log.content.includes('WARN');
                    return (
                      <div 
                        key={log.id} 
                        onClick={() => setLogContent(log.content)}
                        className="group flex gap-3 hover:bg-white/[0.03] cursor-pointer rounded px-2 py-0.5 transition-all"
                      >
                        <span className="text-slate-600 shrink-0">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
                        <span className={`break-all ${isError ? 'text-rose-400' : isWarn ? 'text-amber-400' : 'text-slate-300'}`}>
                          {log.content}
                        </span>
                        <ArrowRight size={10} className="ml-auto text-slate-600 opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-3">
              {sampleLogs.map((log) => {
                const isSelected = selectedSample === log.id;
                const colors = severityColors[log.severity];
                return (
                  <button
                    key={log.id}
                    onClick={() => setSelectedSample(isSelected ? null : log.id)}
                    className={`text-left p-4 rounded-xl border transition-all duration-200 ${
                      isSelected
                        ? 'border-blue-500/40 bg-blue-500/5'
                        : 'border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04]'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span className="pulse-dot" style={{ backgroundColor: colors.dot }} />
                      <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: colors.text }}>
                        {log.severity}
                      </span>
                      <span className="text-[10px] text-slate-600 ml-auto">{log.source}</span>
                    </div>
                    <p className="text-sm font-medium text-slate-300 leading-snug">{log.title}</p>
                    <p className="text-xs text-slate-500 mt-1 line-clamp-2">{log.description}</p>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Pipeline */}
      <div ref={pipelineRef}>
        <PipelineProgress />
      </div>

      {/* Bottom CTA when done */}
      {pipelineStatus === 'completed' && (
        <div className="animate-fade-in space-y-4">
          <div className="mx-auto w-fit flex items-center gap-2 px-6 py-3 rounded-2xl glass border-emerald-500/20">
            <Brain size={18} className="text-emerald-400" />
            <span className="text-sm text-slate-300">Pipeline complete — all agents have processed the incident</span>
          </div>
          {analysisResult && (
            <ApiResultReport result={analysisResult} />
          )}
        </div>
      )}
    </div>
  );
}
