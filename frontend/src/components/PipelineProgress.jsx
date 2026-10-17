import { useRef, useEffect } from 'react';
import gsap from 'gsap';
import { Play, RotateCcw, ShieldAlert, ShieldCheck } from 'lucide-react';
import { useStore } from '../store';
import { agentConfig } from '../data/mockData';
import AgentCard from './AgentCard';

export default function PipelineProgress() {
  const {
    pipelineStatus, agents, startPipeline, resetPipeline,
    runMeta, approval, decideApproval, requireApproval, setRequireApproval,
  } = useStore();
  const redactionTotal = runMeta ? Object.values(runMeta.redactions || {}).reduce((a, b) => a + b, 0) : 0;
  const containerRef = useRef(null);
  const cardsRef = useRef([]);
  const buttonRef = useRef(null);
  const connectorRef = useRef([]);

  useEffect(() => {
    if (pipelineStatus === 'running') {
      gsap.fromTo(
        cardsRef.current.filter(Boolean),
        { y: 30, opacity: 0, scale: 0.9 },
        {
          y: 0,
          opacity: 1,
          scale: 1,
          duration: 0.45,
          stagger: 0.08,
          ease: 'back.out(1.4)',
        }
      );
    }
    if (pipelineStatus === 'completed') {
      gsap.to(buttonRef.current, {
        scale: 1.05,
        duration: 0.3,
        yoyo: true,
        repeat: 1,
        ease: 'power2.inOut',
      });
    }
  }, [pipelineStatus]);

  return (
    <div ref={containerRef} className="space-y-12">
      {/* Header */}
      <div className="flex flex-col items-center text-center gap-6">
        <div className="space-y-1">
          <h3 className="text-xl font-bold text-slate-200 tracking-tight">Pipeline Execution</h3>
          <p className="text-sm text-slate-500 max-w-md">
            {pipelineStatus === 'idle' && 'Configure input and analyze to start the automated multi-agent triage'}
            {pipelineStatus === 'running' && 'Agents are orchestrating your incident response...'}
            {pipelineStatus === 'completed' && 'Analysis complete. Incident fully processed.'}
          </p>
        </div>
        <button
          ref={buttonRef}
          onClick={pipelineStatus === 'running' ? undefined : pipelineStatus === 'completed' ? resetPipeline : startPipeline}
          disabled={pipelineStatus === 'running'}
          className={`flex items-center gap-2 px-8 py-3.5 rounded-2xl text-base font-semibold transition-all duration-300 ${
            pipelineStatus === 'running'
              ? 'bg-slate-700/30 text-slate-500 cursor-not-allowed'
              : pipelineStatus === 'completed'
              ? 'bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 border border-amber-500/20'
              : 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-500 hover:to-indigo-500 shadow-xl shadow-blue-600/20 hover:scale-105 active:scale-95'
          }`}
        >
          {pipelineStatus === 'idle' && <><Play size={18} fill="currentColor" /> Start Analysis</>}
          {pipelineStatus === 'running' && 'Processing...'}
          {pipelineStatus === 'completed' && <><RotateCcw size={18} /> Run New Analysis</>}
        </button>
        {pipelineStatus === 'idle' && (
          <label className="flex items-center gap-2 text-xs text-slate-500 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={requireApproval}
              onChange={(e) => setRequireApproval(e.target.checked)}
              className="accent-amber-500"
            />
            Hold P1/P2 Jira ticket and alerts until I approve
          </label>
        )}
      </div>

      {/* Agent Cards */}
      <div className="flex items-center justify-center gap-0 overflow-x-auto pb-4">

        {agentConfig.map((agent, i) => (
          <div key={agent.id} className="flex items-center">
            <AgentCard
              ref={(el) => (cardsRef.current[i] = el)}
              agent={{ ...agents[i], icon: agent.icon }}
              index={i}
              isActive={i === useStore.getState().currentAgentIndex}
            />
            {i < agentConfig.length - 1 && (
              <div
                ref={(el) => (connectorRef.current[i] = el)}
                className={`w-6 h-px transition-colors duration-500 ${
                  agents[i]?.status === 'done' ? 'bg-emerald-500/40' : 'bg-white/[0.06]'
                }`}
              />
            )}
          </div>
        ))}
      </div>

      {/* Data-handling notices from the server */}
      {runMeta && (redactionTotal > 0 || runMeta.injectionSuspected) && (
        <div className="mx-auto max-w-2xl space-y-1 text-center text-xs text-slate-500">
          {redactionTotal > 0 && (
            <p className="flex items-center justify-center gap-1.5">
              <ShieldCheck size={13} className="text-emerald-500" />
              {redactionTotal} secret/PII value{redactionTotal === 1 ? '' : 's'} masked before analysis
              ({Object.entries(runMeta.redactions).map(([k, v]) => `${k.toLowerCase().replace(/_/g, ' ')} x${v}`).join(', ')})
            </p>
          )}
          {runMeta.injectionSuspected && (
            <p className="flex items-center justify-center gap-1.5 text-amber-400">
              <ShieldAlert size={13} />
              Log text that reads like instructions to an AI was detected and treated as plain evidence
            </p>
          )}
        </div>
      )}

      {/* Human approval gate */}
      {approval && approval.status !== 'approved' && approval.status !== 'rejected' && (
        <div className="mx-auto max-w-xl rounded-2xl border border-amber-500/30 bg-amber-500/10 p-5 text-center space-y-3">
          <p className="text-sm font-semibold text-amber-300">Analysis complete. Waiting for your approval</p>
          <p className="text-xs text-slate-400">
            This is a P1/P2 incident. The JIRA ticket and alert have not been sent yet.
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={() => decideApproval(true)}
              disabled={approval.status === 'approving'}
              className="rounded-xl bg-amber-500 px-5 py-2 text-sm font-semibold text-slate-900 hover:bg-amber-400 disabled:opacity-50"
            >
              {approval.status === 'approving' ? 'Sending...' : 'Approve and notify'}
            </button>
            <button
              onClick={() => decideApproval(false)}
              disabled={approval.status === 'approving'}
              className="rounded-xl border border-white/10 px-5 py-2 text-sm text-slate-300 hover:bg-white/5 disabled:opacity-50"
            >
              Discard
            </button>
          </div>
        </div>
      )}
      {approval && (approval.status === 'approved' || approval.status === 'rejected') && (
        <p className="text-center text-xs text-slate-500">
          {approval.status === 'approved' ? 'Approved: JIRA ticket and alert sent.' : 'Discarded: no JIRA ticket or alert was sent.'}
        </p>
      )}
    </div>
  );
}
