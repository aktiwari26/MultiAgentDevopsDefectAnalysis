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

        // Mirrors the real LangGraph pipeline (devops_graph.py):
        // classifier -> severity -> root_cause -> remediation -> cookbook (runbook)
        // -> jira (P1/P2 only) -> notification (Jira first, so the alert carries the ticket key).
        const nodeDefs = [
            { id: 'input', label: 'Log Input', sub: 'paste or upload', icon: '📝', color: '#00f2fe' },
            { id: 'classifier', label: 'Classifier', sub: 'log type + summary', icon: '🏷️', color: '#4facfe' },
            { id: 'severity', label: 'Severity', sub: 'P1–P4 triage', icon: '⚠️', color: '#4facfe' },
            { id: 'rootcause', label: 'Root Cause', sub: 'all severities', icon: '🔍', color: '#b026ff' },
            { id: 'remediation', label: 'Remediation', sub: 'fix plan + commands', icon: '🔧', color: '#b026ff' },
            { id: 'runbook', label: 'Runbook', sub: 'all severities', icon: '📖', color: '#ff9900' },
            { id: 'jira', label: 'JIRA Ticket', sub: 'P1/P2 only', icon: '🎫', color: '#00f260' },
            { id: 'notification', label: 'Notification', sub: 'n8n, Slack fallback', icon: '🔔', color: '#ff4b2b' }
        ];

        const desktopPos = {
            input: [13, 16], classifier: [38, 16], severity: [63, 16], rootcause: [88, 16],
            runbook: [38, 50], remediation: [88, 50],
            jira: [13, 84], notification: [63, 84]
        };
        const mobilePos = {
            input: [27, 12], classifier: [73, 12],
            rootcause: [27, 37], severity: [73, 37],
            remediation: [27, 62], runbook: [73, 62],
            jira: [27, 87], notification: [73, 87]
        };

        function getNodes() {
            const pos = window.innerWidth < 768 ? mobilePos : desktopPos;
            return nodeDefs.map(n => ({ ...n, x: pos[n.id][0], y: pos[n.id][1] }));
        }

        let nodes = getNodes();

        const links = [
            { source: 'input', target: 'classifier', color: '#00f2fe' },
            { source: 'classifier', target: 'severity', color: '#4facfe' },
            { source: 'severity', target: 'rootcause', color: '#b026ff' },
            { source: 'rootcause', target: 'remediation', color: '#b026ff' },
            { source: 'remediation', target: 'runbook', color: '#ff9900' },
            { source: 'runbook', target: 'jira', color: '#00f260', label: 'P1 / P2 only' },
            { source: 'runbook', target: 'notification', color: '#ff4b2b' }
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
                    <div class="node-sub">${node.sub}</div>
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

                if (link.label) {
                    const isVertical = Math.abs(tx - sx) < 20;
                    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                    text.setAttribute('class', 'link-label');
                    text.setAttribute('x', isVertical ? (sx + tx) / 2 - 10 : (sx + tx) / 2);
                    text.setAttribute('y', isVertical ? (sy + ty) / 2 : (sy + ty) / 2 - 10);
                    text.setAttribute('text-anchor', isVertical ? 'end' : 'middle');
                    text.setAttribute('fill', link.color);
                    text.textContent = link.label;
                    svgGroup.appendChild(text);
                }
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
                        labels: ['Manual SRE', 'Legacy Automation', 'DevOps (target)'],
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
                            label: 'Accuracy (%, illustrative)',
                            data: [82, 89, 94, 98],
                            borderColor: '#00f260',
                            backgroundColor: 'rgba(0, 242, 96, 0.1)',
                            fill: true,
                            tension: 0.4
                        }, {
                            label: 'Cost ($, illustrative)',
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
                                <span className="stat-value">&lt;60s</span>
                                <span className="stat-label">Typical Analysis Time</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-value">7</span>
                                <span className="stat-label">AI Agents</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-value">P1–P4</span>
                                <span className="stat-label">Severity Triage</span>
                            </div>
                        </div>
                    </div>
                    <div className="architecture-wrap">
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
                        <p className="graphic-caption">
                            Simplified view of the live pipeline. Hover a stage to highlight its connections;
                            the moving light shows the direction of data flow. Every log gets Root Cause and
                            Remediation; severity decides whether a JIRA ticket is filed (P1/P2 only).
                        </p>
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
                                        <h3>MTTR Comparison (Minutes) <span className="illustrative-badge">Illustrative</span></h3>
                                        <canvas id="mttrChart"></canvas>
                                        <p className="graphic-caption">
                                            MTTR = Mean Time To Resolution. Illustrative targets showing the intended effect
                                            of automation, not measured results; real figures depend on your incident mix.
                                        </p>
                                    </div>
                                    <div className="chart-item">
                                        <h3>Agent Accuracy vs Cost <span className="illustrative-badge">Illustrative</span></h3>
                                        <canvas id="costChart"></canvas>
                                        <p className="graphic-caption">
                                            Sample trend showing accuracy improving as prompts and knowledge base are tuned
                                            while cost falls. Not measured data.
                                        </p>
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
                                            <div className="bp-node highlight">Root Cause</div>
                                            <div className="bp-arrow">↓</div>
                                            <div className="bp-node highlight">Remediation</div>
                                            <div className="bp-arrow">↓</div>
                                            <div className="bp-node">Runbook</div>
                                        </div>
                                        <p className="graphic-caption">
                                            Every log is classified and triaged first, then runs through Root Cause,
                                            Remediation and Runbook regardless of severity.
                                        </p>
                                    </div>
                                    <div className="diagram-item blueprint-card">
                                        <h3>Ticket, then Alert</h3>
                                        <div className="blueprint-flow">
                                            <div className="bp-step">Runbook</div>
                                            <div className="bp-arrow">→</div>
                                            <div className="bp-step">JIRA (P1/P2)</div>
                                            <div className="bp-arrow">→</div>
                                            <div className="bp-step">Notification</div>
                                        </div>
                                        <p className="graphic-caption">
                                            Once the Runbook is ready the JIRA ticket is filed (P1/P2 only), then the
                                            n8n/Slack alert is sent with the ticket key. Repeat incidents reuse the
                                            ticket and are not re-alerted.
                                        </p>
                                    </div>
                                </div>
                            </div>
                            <div className="tab-content" id="agents">
                                <div className="agent-roster-grid">
                                    {[
                                        { id: 1, name: "Classifier", node: "classifier", role: "Categorise log type; structured summary" },
                                        { id: 2, name: "Severity Assessor", node: "severity", role: "Assign P1–P4 triage; set approval status" },
                                        { id: 3, name: "Root Cause Analyst", node: "root_cause", role: "RCA grounded in a runbook knowledge base (keyword retrieval)" },
                                        { id: 4, name: "Remediation Planner", node: "remediation", role: "Step-by-step remediation planning" },
                                        { id: 5, name: "Cookbook Synthesizer", node: "cookbook", role: "Operational runbook / SOP generation" },
                                        { id: 6, name: "JIRA Agent", node: "jira", role: "Creates ADF-formatted JIRA tickets" },
                                        { id: 7, name: "Notification Agent", node: "notification", role: "Alert via n8n webhook; Slack Block Kit fallback" }
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
                                            <li>Specialized agents with severity-based routing</li>
                                            <li>Alerts carry the JIRA key; repeat incidents are de-duplicated</li>
                                            <li>Per-stage status and timing in every run</li>
                                        </ul>
                                    </div>
                                    <div className="swot-card weakness">
                                        <h4>Weaknesses</h4>
                                        <ul>
                                            <li>Keyword-only retrieval over a small knowledge base</li>
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
                            { name: 'LangGraph', role: 'Agent Orchestration', desc: 'Stateful agent graph with severity routing' },
                            { name: 'Knowledge Base', role: 'RAG Retrieval', desc: 'Keyword search over runbooks (vector index planned)' },
                            { name: 'FastAPI', role: 'Operational API', desc: 'Streams results to the dashboard via SSE' },
                            { name: 'OpenRouter', role: 'LLM Gateway', desc: 'One API key, many models' },
                            { name: 'Local Models', role: 'Optional Inference', desc: 'Any OpenAI-compatible endpoint via base URL' },
                            { name: 'LangSmith', role: 'Observability (optional)', desc: 'Trace analysis when configured' },
                            { name: 'JIRA Cloud', role: 'Ticketing', desc: 'Auto-files P1/P2 incident tickets' },
                            { name: 'React + Vite', role: 'Console UI', desc: 'Modern reactive dashboard' },
                            { name: 'n8n', role: 'Automation', desc: 'Alert webhook with Slack fallback' },
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
								name: "Sachin Jain",
								role: "Principal Architect",
								initial: "SJ",
								colors: "#4facfe, #b026ff",
								image: "/Sachin.jpg",
								linkedin: "https://www.linkedin.com/in/sachin-jain-0a02965",
								github: "",
								website: "",
								x: "",
								"dev.to": "",
								Bio: "Principal Architect"
                            },
                            {
								 name: "Prashant Agarwal",
								role: "Backend Dev and AI Learner",
								initial: "PA",
								colors: "#4facfe, #b026ff",
								image: "/Prashant.png",
								linkedin: "https://www.linkedin.com/in/prashantagarw10/",
								github: "",
								website: "",
								x: "",
								"dev.to": "",
								Bio: "Associate Director"
							},
                            {
								name: "Ashish Garg",
								role: "Technical Manager",
								initial: "AG",
								colors: "#4facfe, #b026ff",
								image: "/Ashish.jpg",
								linkedin: "Ashish Garg - Iris Software Inc. | LinkedIn",
								github: "",
								website: "",
								x: "",
								"dev.to": "",
								Bio: "Associate Director"
                            },
                            {
                                name: "Ajeet Kumar Tiwari",
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
								name: "RaviShankar Kutty",
								role: "AI Learner",
								initial: "RK",
								colors: "#4facfe, #b026ff",
								image: "/Ravi.png",
								linkedin: "https://www.linkedin.com/in/ravi-shankar-68784a44",
								github: "",
								website: "",
								x: "",
								"dev.to": "",
								Bio: "Senior Director"
							},
                            {
                                name: "Chirag Jehanabadi",
                                role: "Director",
                                initial: "CJ",
                                colors: "#f8b500, #00f260",
                                image: "/Chirag.png",
                                linkedin: "https://www.linkedin.com/in/ravi-shankar-68784a44",
                                github: "",
                                website: "",
                                x: "",
                                "dev.to": "",
                                Bio: "Director"
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
                                        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-wrap items-center justify-center gap-1 p-1">
                                            {member.github && <a href={member.github} target="_blank" rel="noreferrer" className="text-white hover:text-blue-400 transition-colors"><Github size={12} /></a>}
                                            {member.linkedin && <a href={member.linkedin} target="_blank" rel="noreferrer" className="text-white hover:text-blue-400 transition-colors"><Linkedin size={12} /></a>}
                                            {member.website && <a href={member.website} target="_blank" rel="noreferrer" className="text-white hover:text-blue-400 transition-colors"><Globe size={12} /></a>}
                                            {member.x && <a href={member.x} target="_blank" rel="noreferrer" className="text-white hover:text-blue-400 transition-colors"><Twitter size={12} /></a>}
                                            {member["dev.to"] && <a href={member["dev.to"]} target="_blank" rel="noreferrer" className="text-white hover:text-blue-400 transition-colors"><Code size={12} /></a>}
                                        </div>
                                    )}
                                </div>
                                <h4><span className="member-initial">{member.name.charAt(0).toUpperCase()}</span>{member.name.slice(1)}</h4>
                                {member.role && <p className="text-[0.6rem] text-blue-400 font-bold uppercase tracking-wider mt-1">{member.role}</p>}
                                {member.Bio && <p className="text-[0.65rem] text-slate-400 mt-1.5 px-1 text-center leading-snug">{member.Bio}</p>}
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
