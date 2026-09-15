"""Knowledge-base retrieval for the Root Cause Analysis stage.

Keyword-frequency search over a corpus of embedded runbook snippets plus
the Markdown files in data/knowledge_base/ — no vector index, no extra
heavyweight dependencies (torch/llama-index/lancedb). This mirrors what
the reference React dashboard's own production app actually runs: its
LanceDB + LlamaIndex + HuggingFace-embeddings pipeline exists only in a
notebook and is never wired into its running FastAPI app either, so
keyword search is the real, load-bearing retrieval path there too. A true
vector index is a documented future enhancement, not required for a
working, LLM-grounded Root Cause
stage.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional, Any

EMBEDDED_KB_DOCS: list[dict] = [
    {
        "title": "Kubernetes CrashLoopBackOff Resolution",
        "content": (
            "CrashLoopBackOff occurs when a pod repeatedly fails and restarts. "
            "Steps: 1) kubectl describe pod <name> — check Events section. "
            "2) kubectl logs <pod> --previous — view crash logs. "
            "3) Common causes: OOMKilled (memory limit), bad config/env vars, "
            "missing secrets, failing readiness probes, app startup errors. "
            "4) Fix OOMKilled: increase memory limits in deployment spec. "
            "5) Fix bad config: kubectl edit deployment or patch env vars. "
            "6) kubectl rollout restart deployment/<name> after fixing."
        ),
    },
    {
        "title": "Redis Connection Pool Exhaustion",
        "content": (
            "Redis NOAUTH / connection pool exhaustion fix: "
            "1) Check active connections: redis-cli INFO clients. "
            "2) Max connections: CONFIG GET maxclients. "
            "3) Increase pool size in app config (e.g., pool_size=50). "
            "4) Enable connection timeout: CONFIG SET timeout 300. "
            "5) Use connection pooling library (redis-py ConnectionPool). "
            "6) Monitor with: redis-cli MONITOR for slow commands. "
            "7) Consider Redis Cluster for horizontal scaling."
        ),
    },
    {
        "title": "PostgreSQL Connection Limit Exceeded",
        "content": (
            "PostgreSQL 'FATAL: remaining connection slots reserved' fix: "
            "1) Check connections: SELECT count(*) FROM pg_stat_activity. "
            "2) Kill idle connections: SELECT pg_terminate_backend(pid) "
            "   FROM pg_stat_activity WHERE state = 'idle' AND query_start < now() - interval '5 min'. "
            "3) Increase max_connections in postgresql.conf (requires restart). "
            "4) Deploy PgBouncer as connection pooler. "
            "5) Set application connection pool max_size to <= max_connections/4."
        ),
    },
    {
        "title": "Nginx 502 Bad Gateway Troubleshooting",
        "content": (
            "Nginx 502 Bad Gateway: upstream service unreachable. "
            "1) Check upstream: curl -v http://upstream-service:port/health. "
            "2) Check Nginx error log: tail -f /var/log/nginx/error.log. "
            "3) Verify upstream is running: systemctl status app-service or kubectl get pods. "
            "4) Increase timeout: proxy_read_timeout 120s; proxy_connect_timeout 120s. "
            "5) Check keepalive: upstream { keepalive 32; }. "
            "6) Enable upstream health checks in Nginx Plus or use load balancer health checks."
        ),
    },
    {
        "title": "Incident Severity Classification (P1-P4)",
        "content": (
            "Severity guidelines: "
            "P1 CRITICAL: Complete outage, data loss risk, payment failure, >50% users impacted — page on-call immediately. "
            "P2 HIGH: Major degradation, >20% error rate, auth outage, partial outage — alert team within 15 min. "
            "P3 MEDIUM: Non-critical service impact, elevated errors <5%, no direct customer impact — fix in 4h. "
            "P4 LOW: Minor warnings, cosmetic issues — schedule in next sprint. "
            "Escalation: On-call → SRE Lead → Infra Lead → Engineering Manager → CTO."
        ),
    },
    {
        "title": "Kubernetes OOMKilled Resolution",
        "content": (
            "OOMKilled: container exceeded memory limit. "
            "1) Check which container: kubectl describe pod <name> | grep -A5 OOMKilled. "
            "2) Get current limits: kubectl get pod <name> -o jsonpath='{.spec.containers[*].resources}'. "
            "3) Check actual usage: kubectl top pod <name>. "
            "4) Increase limits via kubectl patch deployment (containers[].resources.limits.memory). "
            "5) Add memory profiling to identify leak if recurring."
        ),
    },
    {
        "title": "Circuit Breaker Pattern for Microservices",
        "content": (
            "Circuit breaker prevents cascade failures. "
            "States: CLOSED (normal), OPEN (failing — reject requests), HALF-OPEN (testing recovery). "
            "Thresholds: Open after 5 failures in 60s window. "
            "Implementation: Python — use 'pybreaker' library. "
            "Node.js — use 'opossum'. "
            "Service mesh: Istio DestinationRule with consecutiveGatewayErrors: 5. "
            "Monitor: Track circuit state changes as a key SRE metric."
        ),
    },
    {
        "title": "Kafka Consumer Lag Remediation",
        "content": (
            "High Kafka consumer lag means consumers cannot keep up with producers. "
            "1) Check lag: kafka-consumer-groups.sh --describe --group <group>. "
            "2) Solutions: increase partitions (kafka-topics.sh --alter), "
            "   scale consumer group horizontally, optimize consumer poll interval. "
            "3) If lag > 1M messages: consider backpressure, dead letter queues, "
            "   or temporary producer throttling. "
            "4) Monitor: consumer_lag metric in Prometheus/Grafana."
        ),
    },
]


def _load_markdown_kb_docs() -> list[dict]:
    """Read data/knowledge_base/*.md into {'title','content'} docs, using
    the filename (title-cased) as the title. Missing directory -> []."""
    kb_dir = Path(__file__).parent / "data" / "knowledge_base"
    docs: list[dict] = []
    if not kb_dir.is_dir():
        return docs
    for path in sorted(kb_dir.glob("*.md")):
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        title = path.stem.replace("_", " ").title()
        docs.append({"title": title, "content": content})
    return docs


# Embedded snippets + the copied runbook Markdown files, combined once at
# import time into the default search corpus.
KB_DOCS: list[dict] = EMBEDDED_KB_DOCS + _load_markdown_kb_docs()


def keyword_search(
    query: str,
    documents: list[dict] | None = None,
    top_k: int = 3,
) -> str:
    """Keyword-frequency search: score = number of query tokens found in
    each doc's content (case-insensitive), return the top_k docs."""
    if documents is None:
        documents = KB_DOCS
    if not query or not documents:
        return "No relevant knowledge base documents found for this query."

    query_tokens = [t.lower() for t in query.split() if t]
    scored: list[tuple[int, str, str]] = []

    for doc in documents:
        content_lower = doc["content"].lower()
        score = sum(1 for token in query_tokens if token in content_lower)
        if score > 0:
            scored.append((score, doc["title"], doc["content"]))

    scored.sort(reverse=True)
    if not scored:
        return "No relevant knowledge base documents found for this query."

    results = [f"[{title}]\n{content}" for _, title, content in scored[:top_k]]
    return "\n\n---\n\n".join(results)


def search_knowledge_base(
    query: str,
    query_engine: Optional[Any] = None,
    top_k: int = 3,
    documents: list[dict] | None = None,
) -> str:
    """Try a query_engine (e.g. a future vector index) first when given;
    always falls back to keyword_search on any failure/empty result."""
    if query_engine is not None:
        try:
            response = query_engine.query(query)
            result = str(response).strip()
            if result:
                return result
        except Exception:
            pass

    return keyword_search(query, documents=documents, top_k=top_k)
