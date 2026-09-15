import React, { useEffect, useState } from "react";
import Chart from "chart.js/auto";
import { useNavigate } from "react-router-dom";
import {
    Terminal, Monitor, Cpu, Shield, Globe, Layers, Zap,
    CheckCircle, ChevronRight, Copy, Apple, Github, Linkedin, Twitter, Code
} from "lucide-react";

import "./LandingPage.css";

export default function LandingPage() {
    const navigate = useNavigate();

    useEffect(() => {
        const container = document.getElementById('architecture');
        const svgGroup = document.getElementById('links-group');
        const nodesGroup = document.getElementById('nodes-group');

        function getNodes() {
            const isMobile = window.innerWidth < 768;
            if (isMobile) {
                return [
                    { id: 'input', label: 'CloudWatch Logs', icon: '📝', x: 50, y: 8, color: '#00f2fe' },
                    { id: 'analyzer', label: 'Log Analyzer', icon: '🔍', x: 25, y: 22, color: '#4facfe' },
                    { id: 'remediation', label: 'Remediation Agent', icon: '🔧', x: 75, y: 22, color: '#4facfe' },
                    { id: 'runbook', label: 'Runbook Gen', icon: '📖', x: 50, y: 40, color: '#b026ff' },
                    { id: 'langsmith', label: 'LangSmith Tracing', icon: '📊', x: 50, y: 56, color: '#ff9900' },
                    { id: 'jira', label: 'JIRA Ticket', icon: '🎫', x: 25, y: 72, color: '#00f260' },
                    { id: 'n8n', label: 'n8n Orchestrator', icon: '🔄', x: 75, y: 72, color: '#ff4b2b' },
                    { id: 'slack', label: 'Slack Alert', icon: '💬', x: 50, y: 88, color: '#00f260' }
                ];
            }
            return [
                { id: 'input', label: 'CloudWatch Logs', icon: '📝', x: 12, y: 50, color: '#00f2fe' },
                { id: 'analyzer', label: 'Log Analyzer', icon: '🔍', x: 32, y: 32, color: '#4facfe' },
                { id: 'remediation', label: 'Remediation Agent', icon: '🔧', x: 32, y: 68, color: '#4facfe' },
                { id: 'runbook', label: 'Runbook Gen', icon: '📖', x: 52, y: 50, color: '#b026ff' },
                { id: 'langsmith', label: 'LangSmith Tracing', icon: '📊', x: 52, y: 15, color: '#ff9900' },
                { id: 'jira', label: 'JIRA Ticket', icon: '🎫', x: 72, y: 32, color: '#00f260' },
                { id: 'n8n', label: 'n8n Orchestrator', icon: '🔄', x: 72, y: 68, color: '#ff4b2b' },
                { id: 'slack', label: 'Slack Alert', icon: '💬', x: 88, y: 50, color: '#00f260' }
            ];
        }

        let nodes = getNodes();

        const links = [
            { source: 'input', target: 'analyzer', color: '#00f2fe' },
            { source: 'input', target: 'remediation', color: '#00f2fe' },
            { source: 'analyzer', target: 'runbook', color: '#4facfe' },
            { source: 'remediation', target: 'runbook', color: '#4facfe' },
            { source: 'analyzer', target: 'langsmith', color: '#ff9900', curve: true },
            { source: 'remediation', target: 'langsmith', color: '#ff9900', curve: true },
            { source: 'runbook', target: 'langsmith', color: '#ff9900' },
            { source: 'runbook', target: 'jira', color: '#b026ff' },
            { source: 'jira', target: 'n8n', color: '#00f260' },
            { source: 'n8n', target: 'slack', color: '#ff4b2b', label: 'Alert Trigger' },
            { source: 'slack', target: 'input', color: '#00f260', curve: true, reverseAnim: true }
        ];

        function hexToRgb(hex) {
            const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
            return result ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}` : '255, 255, 255';
        }

        function highlightNodes(sourceId, targetId, color) {
            const allNodes = document.querySelectorAll('.node-card');
            allNodes.forEach(node => {
                const id = node.getAttribute('data-id');
                if (id === sourceId || id === targetId) {
                    node.style.borderColor = color;
                    node.style.boxShadow = `0 10px 30px rgba(${hexToRgb(color)}, 0.5)`;
                } else {
                    node.style.opacity = '0.3';
                }
            });
        }

        function resetNodes() {
            const allNodes = document.querySelectorAll('.node-card');
            allNodes.forEach(node => {
                const nodeData = nodes.find(n => n.id === node.getAttribute('data-id'));
                node.style.borderColor = `rgba(${hexToRgb(nodeData.color)}, 0.3)`;
                node.style.boxShadow = `0 4px 20px rgba(${hexToRgb(nodeData.color)}, 0.1)`;
                node.style.opacity = '1';
            });
        }

        function highlightLinks(nodeId, linkIdx = null) {
            const lights = document.querySelectorAll('.tube-light');
            const bases = document.querySelectorAll('.tube-base');
            lights.forEach((light, idx) => {
                let isConnected = false;
                if (linkIdx !== null) {
                    isConnected = (idx === linkIdx);
                } else {
                    isConnected = (light.getAttribute('data-source') === nodeId || light.getAttribute('data-target') === nodeId);
                    if (isConnected) {
                        const otherNodeId = light.getAttribute('data-source') === nodeId ? light.getAttribute('data-target') : light.getAttribute('data-source');
                        const otherNode = document.querySelector(`.node-card[data-id="${otherNodeId}"]`);
                        const color = light.getAttribute('data-color');
                        if (otherNode) {
                            otherNode.style.borderColor = color;
                            otherNode.style.boxShadow = `0 10px 30px rgba(${hexToRgb(color)}, 0.4)`;
                        }
                    }
                }
                if (isConnected) {
                    light.style.opacity = '1';
                    light.style.strokeWidth = '6px';
                    bases[idx].style.opacity = '0.5';
                } else {
                    light.style.opacity = '0.05';
                    bases[idx].style.opacity = '0.05';
                }
            });
        }

        function resetLinks() {
            const lights = document.querySelectorAll('.tube-light');
            const bases = document.querySelectorAll('.tube-base');
            lights.forEach(light => light.style.opacity = '1');
            bases.forEach(base => base.style.opacity = '0.15');
        }

        function renderNodes() {
            if (!nodesGroup) return;
            nodes = getNodes();
            nodesGroup.innerHTML = '';
            nodes.forEach(node => {
                const el = document.createElement('div');
                el.className = 'node-card';
                el.setAttribute('data-id', node.id);
                el.style.left = `${node.x}%`;
                el.style.top = `${node.y}%`;
                el.style.borderColor = `rgba(${hexToRgb(node.color)}, 0.3)`;
                el.style.boxShadow = `0 4px 20px rgba(${hexToRgb(node.color)}, 0.1)`;
                el.innerHTML = `
                    <div class="node-icon" style="color: ${node.color}; text-shadow: 0 0 15px ${node.color};">${node.icon}</div>
                    <div class="node-label">${node.label}</div>
                `;
                el.addEventListener('mouseenter', () => {
                    el.style.borderColor = node.color;
                    el.style.boxShadow = `0 10px 30px rgba(${hexToRgb(node.color)}, 0.5)`;
                    highlightLinks(node.id);
                });
                el.addEventListener('mouseleave', () => {
                    resetNodes();
                    resetLinks();
                });
                nodesGroup.appendChild(el);
            });
        }

        function renderLinks() {
            if (!svgGroup || !container) return;
            svgGroup.innerHTML = '';
            const rect = container.getBoundingClientRect();
            links.forEach((link, idx) => {
                const sourceNode = nodes.find(n => n.id === link.source);
                const targetNode = nodes.find(n => n.id === link.target);
                const sx = (sourceNode.x / 100) * rect.width;
                const sy = (sourceNode.y / 100) * rect.height;
                const tx = (targetNode.x / 100) * rect.width;
                const ty = (targetNode.y / 100) * rect.height;
                let pathD = '';
                if (link.curve) {
                    const curveHeight = sourceNode.id === 'langsmith' || targetNode.id === 'langsmith' ? 80 : Math.min(220, rect.height * 0.45);
                    pathD = `M ${sx} ${sy} C ${sx} ${sy - curveHeight}, ${tx} ${ty - curveHeight}, ${tx} ${ty}`;
                } else {
                    const dx = tx - sx;
                    const dy = ty - sy;
                    if (Math.abs(dx) < 20) {
                        pathD = `M ${sx} ${sy} C ${sx + 15} ${sy + dy / 2}, ${tx - 15} ${sy + dy / 2}, ${tx} ${ty}`;
                    } else if (Math.abs(dy) < 10) {
                        pathD = `M ${sx} ${sy} C ${sx + dx / 2} ${sy + 15}, ${tx - dx / 2} ${ty - 15}, ${tx} ${ty}`;
                    } else {
                        pathD = `M ${sx} ${sy} C ${sx + dx / 2} ${sy}, ${tx - dx / 2} ${ty}, ${tx} ${ty}`;
                    }
                }
                const baseNode = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                baseNode.setAttribute('d', pathD);
                baseNode.setAttribute('class', 'tube-base');
                baseNode.setAttribute('stroke', link.color);
                const lightNode = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                lightNode.setAttribute('d', pathD);
                let lightClass = 'tube-light';
                if (link.reverseAnim) lightClass += ' reverse';
                lightNode.setAttribute('class', lightClass);
                lightNode.setAttribute('stroke', link.color);
                lightNode.setAttribute('filter', 'url(#glow-strong)');
                lightNode.setAttribute('data-source', link.source);
                lightNode.setAttribute('data-target', link.target);
                lightNode.setAttribute('data-color', link.color);
                lightNode.addEventListener('mouseenter', () => {
                    highlightNodes(link.source, link.target, link.color);
                    highlightLinks(null, idx);
                });
                lightNode.addEventListener('mouseleave', () => {
                    resetNodes();
                    resetLinks();
                });
                svgGroup.appendChild(baseNode);
                svgGroup.appendChild(lightNode);
            });
        }

        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const target = btn.getAttribute('data-tab');
                tabBtns.forEach(b => b.classList.remove('active'));
                tabContents.forEach(c => c.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById(target).classList.add('active');
            });
        });

        function initCharts() {
            const mttrChartEl = document.getElementById('mttrChart');
            if (mttrChartEl) {
                new Chart(mttrChartEl.getContext('2d'), {
                    type: 'bar',
                    data: {
                        labels: ['Manual SRE', 'Legacy Automation', 'DevOps'],
                        datasets: [{
                            label: 'MTTR (min)',
                            data: [120, 45, 4],
                            backgroundColor: ['rgba(148, 163, 184, 0.2)', 'rgba(79, 172, 254, 0.2)', 'rgba(0, 242, 254, 0.6)'],
                            borderColor: ['#94a3b8', '#4facfe', '#00f2fe'],
                            borderWidth: 2
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                            x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
                        },
                        plugins: { legend: { display: false } }
                    }
                });
            }
            const costChartEl = document.getElementById('costChart');
            if (costChartEl) {
                new Chart(costChartEl.getContext('2d'), {
                    type: 'line',
                    data: {
                        labels: ['W1', 'W2', 'W3', 'W4'],
                        datasets: [{
                            label: 'Accuracy (%)',
                            data: [82, 89, 94, 98],
                            borderColor: '#00f260',
                            backgroundColor: 'rgba(0, 242, 96, 0.1)',
                            fill: true,
                            tension: 0.4
                        }, {
                            label: 'Cost ($)',
                            data: [40, 32, 28, 22],
                            borderColor: '#ff4b2b',
                            borderDash: [5, 5],
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                            x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
                        },
                        plugins: { legend: { labels: { color: '#94a3b8' } } }
                    }
                });
            }
        }

        let resizeTimer;
        let linkTimeout;
        const handleResize = () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                renderNodes();
                renderLinks();
            }, 100);
        };
        window.addEventListener('resize', handleResize);
        renderNodes();
        linkTimeout = setTimeout(renderLinks, 50);
        initCharts();

        return () => {
            window.removeEventListener('resize', handleResize);
            clearTimeout(resizeTimer);
            clearTimeout(linkTimeout);
            const mttrCanvas = document.getElementById('mttrChart');
            if (mttrCanvas) {
                const chartInstance = Chart.getChart(mttrCanvas);
                if (chartInstance) chartInstance.destroy();
            }
            const costCanvas = document.getElementById('costChart');
            if (costCanvas) {
                const chartInstance = Chart.getChart(costCanvas);
                if (chartInstance) chartInstance.destroy();
            }
        };
    }, []);

    return (
        <div className="landing-page-wrapper">
            <style>{`
                .landing-page-wrapper {
                    min-height: 100vh;
                    overflow-x: hidden;
                    position: relative;
                }
            `}</style>
            <div className="background-grid"></div>
            <div className="ambient-glow glow-1"></div>
            <div className="ambient-glow glow-2"></div>
            <div className="ambient-glow glow-3"></div>
            <header className="navbar">
                <div className="logo">
                    <img src="logo_nobg.png" alt="DevOps Logo" />
                    <span className="logo-text">DevOps</span>
                </div>
                <nav>
                    <a href="#architecture">Architecture</a>
                    <a href="#pipeline">Pipeline</a>
                    <a href="/Official_Documentation.html" target="_blank" rel="noopener noreferrer">Official Documentation</a>
                    <a href="#team">The Team</a>
                </nav>
                <button className="cta-button" onClick={() => navigate("/dashboard")}>Launch Dashboard</button>
            </header>
            <main>
                <section className="hero">
                    <div className="hero-content">
                        <div className="badge">
                            <span className="badge-dot"></span> AI Post-Training Hackathon
                        </div>
                        <h1>Automating DevOps<br />with <span className="gradient-text">Agentic Intelligence</span></h1>
                        <p>Modern production systems generate thousands of log lines per minute. <strong>DevOps</strong> transforms raw log streams into decisive action in under 60 seconds.</p>
                        <div className="hero-buttons">
                            <button className="primary-btn" onClick={() => navigate("/dashboard")}>Launch Dashboard</button>
                            <a href="/Official_Documentation.html" target="_blank" rel="noopener noreferrer" className="secondary-btn">Official Documentation</a>
                        </div>
                        <div className="stats-container">
                            <div className="stat-item">
                                <span className="stat-value">60s</span>
                                <span className="stat-label">Analysis Time</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-value">7</span>
                                <span className="stat-label">AI Agents</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-value">100%</span>
                                <span className="stat-label">Traceability</span>
                            </div>
                        </div>
                    </div>
                    <div className="architecture-visual" id="architecture">
                        <svg id="network-svg">
                            <defs>
                                <filter id="glow-strong" x="-50%" y="-50%" width="200%" height="200%">
                                    <feGaussianBlur stdDeviation="6" result="blur" />
                                    <feMerge>
                                        <feMergeNode in="blur" />
                                        <feMergeNode in="blur" />
                                        <feMergeNode in="SourceGraphic" />
                                    </feMerge>
                                </filter>
                            </defs>
                            <g id="links-group"></g>
                        </svg>
                        <div id="nodes-group"></div>
                    </div>
                </section>

                <section className="strategy-section" id="strategy">
                    <div className="section-title">
                        <h2>3-Tier <span>Agentic Strategy</span></h2>
                        <p>High-fidelity reasoning powered by specialized models.</p>
                    </div>
                    <div className="strategy-grid">
                        <div className="strategy-item tier-fast">
                            <div className="tier-badge">Tier 1: Fast</div>
                            <h4>LLM Fast</h4>
                            <p className="model-name">gpt-4o-mini (Temp: 0.1)</p>
                            <ul className="tier-list">
                                <li>Incident Classification</li>
                                <li>Severity Assessment</li>
                                <li>Fast Triage</li>
                            </ul>
                        </div>
                        <div className="strategy-item tier-reasoning">
                            <div className="tier-badge">Tier 2: Reasoning</div>
                            <h4>LLM Reasoning</h4>
                            <p className="model-name">gpt-4o (Temp: 0.2)</p>
                            <ul className="tier-list">
                                <li>RAG-Grounded RCA</li>
                                <li>Remediation Planning</li>
                                <li>Knowledge Synthesis</li>
                            </ul>
                        </div>
                        <div className="strategy-item tier-gen">
                            <div className="tier-badge">Tier 3: Generation</div>
                            <h4>LLM Generation</h4>
                            <p className="model-name">gpt-4o-mini (Temp: 0.3)</p>
                            <ul className="tier-list">
                                <li>Runbook Synthesis</li>
                                <li>SOP Documentation</li>
                                <li>Stakeholder Updates</li>
                            </ul>
                        </div>
                    </div>
                </section>

                <section className="blueprint-section" id="blueprint">
                    <div className="section-title">
                        <h2>Technical <span>Blueprint</span></h2>
                        <p>Orchestration, data models, and agent workflows.</p>
                    </div>
                    <div className="blueprint-tabs-container">
                        <div className="blueprint-tabs">
                            <button className="tab-btn active" data-tab="performance">Performance</button>
                            <button className="tab-btn" data-tab="flow">Workflows</button>
                            <button className="tab-btn" data-tab="agents">Agent Roster</button>
                            <button className="tab-btn" data-tab="swot">SWOT Analysis</button>
                        </div>
                        <div className="tab-content-container">
                            <div className="tab-content active" id="performance">
                                <div className="chart-grid">
                                    <div className="chart-item">
                                        <h3>MTTR Comparison (Minutes)</h3>
                                        <canvas id="mttrChart"></canvas>
                                    </div>
                                    <div className="chart-item">
                                        <h3>Agent Accuracy vs Cost</h3>
                                        <canvas id="costChart"></canvas>
                                    </div>
                                </div>
                            </div>
                            <div className="tab-content" id="flow">
                                <div className="diagram-grid">
                                    <div className="diagram-item blueprint-card">
                                        <h3>StateGraph Orchestration</h3>
                                        <div className="blueprint-flow vertical">
                                            <div className="bp-node">Classifier</div>
                                            <div className="bp-arrow">↓</div>
                                            <div className="bp-node">Severity</div>
                                            <div className="bp-arrow">↓</div>
                                            <div className="bp-split">
                                                <div className="bp-node highlight">RCA (P1/P2)</div>
                                                <div className="bp-node">Cookbook (P3/P4)</div>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="diagram-item blueprint-card">
                                        <h3>Parallel Fan-out</h3>
                                        <div className="blueprint-flow">
                                            <div className="bp-step">Cookbook</div>
                                            <div className="bp-arrow">→</div>
                                            <div className="bp-split">
                                                <div className="bp-step">JIRA</div>
                                                <div className="bp-step">Slack</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div className="tab-content" id="agents">
                                <div className="agent-roster-grid">
                                    {[
                                        { id: 1, name: "Classifier", node: "classifier", role: "Categorise log type; structured summary" },
                                        { id: 2, name: "Severity Assessor", node: "severity", role: "Assign P1–P4 triage; set approval status" },
                                        { id: 3, name: "Root Cause Analyst", node: "root_cause", role: "RAG-grounded RCA from LanceDB" },
                                        { id: 4, name: "Remediation Planner", node: "remediation", role: "Step-by-step remediation planning" },
                                        { id: 5, name: "Cookbook Synthesizer", node: "cookbook", role: "Operational runbook / SOP generation" },
                                        { id: 6, name: "JIRA Agent", node: "jira", role: "Creates ADF-formatted JIRA tickets" },
                                        { id: 7, name: "Notification Agent", node: "notification", role: "Slack Block Kit alert via n8n" }
                                    ].map(agent => (
                                        <div className="agent-roster-card" key={agent.id}>
                                            <div className="agent-id">#{agent.id}</div>
                                            <h4>{agent.name}</h4>
                                            <code className="node-name">node: {agent.node}</code>
                                            <p>{agent.role}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="tab-content" id="swot">
                                <div className="swot-grid">
                                    <div className="swot-card strength">
                                        <h4>Strengths</h4>
                                        <ul>
                                            <li>Multi-agent parallel processing</li>
                                            <li>Real-time n8n orchestration</li>
                                            <li>LangSmith full traceability</li>
                                        </ul>
                                    </div>
                                    <div className="swot-card weakness">
                                        <h4>Weaknesses</h4>
                                        <ul>
                                            <li>Initial indexing latency (RAG)</li>
                                            <li>Higher token cost for deep reasoning</li>
                                        </ul>
                                    </div>
                                    <div className="swot-card opportunity">
                                        <h4>Opportunities</h4>
                                        <ul>
                                            <li>Infrastructure self-healing</li>
                                            <li>Historical incident correlation</li>
                                        </ul>
                                    </div>
                                    <div className="swot-card threat">
                                        <h4>Threats</h4>
                                        <ul>
                                            <li>LLM hallucination risks</li>
                                            <li>Dynamic system drift</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <section className="tech-stack-section" id="tech">
                    <div className="section-title">
                        <h2>Engineered for <span>Intelligence</span></h2>
                        <p>A production-ready stack built for the AI Post-Training Hackathon.</p>
                    </div>
                    <div className="tech-grid">
                        {[
                            { name: 'LangGraph', role: 'Agent Orchestration', desc: 'Cyclic DAG state machines' },
                            { name: 'LanceDB', role: 'Vector Store', desc: 'Local serverless RAG' },
                            { name: 'FastAPI', role: 'Operational API', desc: 'High-speed Python backend' },
                            { name: 'OpenRouter', role: 'LLM Gateway', desc: 'Cross-platform workflows' },
                            { name: 'Ollama', role: 'Local Inference', desc: 'Air-gapped model execution' },
                            { name: 'LangSmith', role: 'Observability', desc: 'Full-chain trace analysis' },
                            { name: 'HuggingFace', role: 'Embeddings', desc: 'Local BGE-small indexing' },
                            { name: 'React + Vite', role: 'Console UI', desc: 'Modern reactive dashboard' },
                            { name: 'n8n', role: 'Automation', desc: 'Cross-platform workflows' },
                        ].map((tech) => (
                            <div key={tech.name} className="tech-card group relative overflow-hidden">
                                <div className="absolute inset-0 bg-blue-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                                <div className="relative z-10">
                                    <h4 className="text-white font-black uppercase tracking-widest text-sm mb-1">{tech.name}</h4>
                                    <p className="text-[10px] text-blue-400 font-bold uppercase tracking-tighter mb-3">{tech.role}</p>
                                    <p className="text-[11px] text-slate-500 leading-relaxed font-medium">{tech.desc}</p>
                                </div>
                                <div className="absolute bottom-0 right-0 p-2 opacity-10 group-hover:opacity-30 transition-opacity">
                                    <Cpu size={24} />
                                </div>
                            </div>
                        ))}
                    </div>
                </section>


                <section className="team-section" id="team">
                    <div className="section-title">
                        <h2>Meet the <span>Team</span></h2>
                        <p>The minds behind the orchestration.</p>
                    </div>
                    <div className="team-grid">
                        {[
                            {
                                name: "Ajeet Tiwari",
                                role: "Full Stack Dev and AI Learner",
                                initial: "AT",
                                colors: "#4facfe, #b026ff",
                                image: "/Ajeet.jpg",
                                linkedin: "https://www.linkedin.com/in/ajeet2608/",
                                github: "https://github.com/aktiwari26",
                                website: "",
                                x: "https://x.com/ajeettiwar41910",
                                "dev.to": "https://dev.to/developerajeet",
                                Bio: "AI Learner & Enjoy strategic thinking both on and off the board."
                            },
                            {
                                name: "Ashish Garg",
                                role: "Full Stack Developer",
                                initial: "CB",
                                colors: "#4facfe, #b026ff",
                                image: "/Charchit.jpg",
                                linkedin: "https://www.linkedin.com/in/charchit-bansal",
                                github: "https://github.com/charchit95",
                                website: "https://charchitbansal.com/",
                                x: "",
                                "dev.to": "",
                                Bio: "Always up for a game of chess and enjoy strategic thinking both on and off the board."
                            },
                            {
                                name: "Ravishankar Kutty",
                                role: "Full Stack Dev and AI Enthusiast",
                                initial: "R",
                                colors: "#b026ff, #00f260",
                                image: "/Rakshit.jpeg",
                                linkedin: "https://www.linkedin.com/in/rakshit-rangarajan/",
                                github: "https://github.com/Rakshit-Rangarajan",
                                website: "https://rakshitr.co.in",
                                x: "",
                                "dev.to": "https://dev.to/whimsical_odyssean",
                                Bio: "Sleep is Overrated Anyways 😁"
                            },
                            {
                                name: "Chirag Jehanabadi",
                                role: "Software Architect",
                                initial: "MD",
                                colors: "#b026ff, #f8b500",
                                image: "/Rakshit.jpeg",
                                linkedin: "https://www.linkedin.com/in/dmonalisa",
                                github: "https://github.com/letusai15/",
                                website: "https://monalisadas-knowme.vercel.app/",
                                x: "https://x.com/MLisa1501",
                                "dev.to": "https://dev.to/letusai15",
                                Bio: "I Coalesce Creativity!"
                            },
                            {
                                name: "Prashant Agarwal",
                                role: "SRE",
                                initial: "PP",
                                colors: "#f8b500, #00f260",
                                image: "/prakash.jpg",
                                linkedin: "https://www.linkedin.com/in/prkshrj/",
                                github: "",
                                website: "",
                                x: "",
                                "dev.to": "",
                                Bio: "\"Engineer by profession, lifelong learner by mindset\" - Exploring the intersection of AI"
                            },
                            {
                                name: "Sachin Jain",
                                role: "Lead Developer",
                                initial: "AS",
                                colors: "#f8b500, #00f260",
                                image: "/Avinash.jpeg",
                                linkedin: "https://www.linkedin.com/in/avinash-shyam-1300ba30/",
                                github: "",
                                website: "",
                                x: "",
                                "dev.to": "",
                                Bio: "Lead mobile Dev/Aspiring AI Dev"
                            }
                        ].map(member => (
                            <div className="team-member group" key={member.name}>
                                <div
                                    className="member-avatar relative overflow-hidden"
                                    style={{ '--bg-gradient': `linear-gradient(135deg, ${member.colors || '#000, #000'})` }}
                                >
                                    {member.image ? (
                                        <img src={member.image} alt={member.name} className="w-full h-full object-cover transition-transform group-hover:scale-110" />
                                    ) : (
                                        member.initial
                                    )}
                                    {(member.github || member.linkedin || member.website || member.x || member["dev.to"]) && (
                                        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-wrap items-center justify-center gap-3 p-2">
                                            {member.github && <a href={member.github} target="_blank" rel="noreferrer" className="text-white hover:text-blue-400 transition-colors"><Github size={18} /></a>}
                                            {member.linkedin && <a href={member.linkedin} target="_blank" rel="noreferrer" className="text-white hover:text-blue-400 transition-colors"><Linkedin size={18} /></a>}
                                            {member.website && <a href={member.website} target="_blank" rel="noreferrer" className="text-white hover:text-blue-400 transition-colors"><Globe size={18} /></a>}
                                            {member.x && <a href={member.x} target="_blank" rel="noreferrer" className="text-white hover:text-blue-400 transition-colors"><Twitter size={18} /></a>}
                                            {member["dev.to"] && <a href={member["dev.to"]} target="_blank" rel="noreferrer" className="text-white hover:text-blue-400 transition-colors"><Code size={18} /></a>}
                                        </div>
                                    )}
                                </div>
                                <h4>{member.name}</h4>
                                {member.role && <p className="text-xs text-blue-400 font-bold uppercase tracking-widest mt-1">{member.role}</p>}
                                {member.Bio && <p className="text-xs text-slate-400 mt-2 px-2 text-center leading-relaxed">{member.Bio}</p>}
                            </div>
                        ))}

                    </div>
                </section>
            </main>
            <footer className="landing-footer">
                <p>&copy; 2026 DevOps. Built for the AI Post-Training Hackathon.</p>
            </footer>
        </div>
    );
}
