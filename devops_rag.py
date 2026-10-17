"""Knowledge-base retrieval for the Root Cause and Remediation stages.

Lexical retrieval (BM25) over a corpus of embedded runbook snippets plus the
Markdown files in data/knowledge_base/, which are split into heading-level
chunks so a query returns the matching *passage* rather than a whole file.
There is no vector index and no heavyweight dependency; a true embedding index
remains a possible future enhancement (see `search_knowledge_base`'s
`query_engine` hook).

What makes lexical retrieval work reasonably here:
  * `build_rag_query` builds the query from the incident's own error evidence
    (issue titles + error lines from the raw log), not from the report heading.
  * Tokenisation splits camelCase/dotted identifiers, drops stopwords and
    numbers, and applies a light stemmer, so "SQLTransientConnectionException"
    can match "connection".
  * BM25 normalises for chunk length, so large catch-all documents no longer
    win every query.

`python -m eval.run_eval` reports recall@k against a labelled case set.
"""
from __future__ import annotations
import math
import re
from collections import Counter
from pathlib import Path
from typing import Optional, Any

from devops_security import looks_like_injection

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


_MAX_CHUNK_CHARS = 1800
_H2_RE = re.compile(r"^##\s+(.+?)\s*$")   # exactly two hashes ('###' does not match)


def _load_markdown_whole_docs() -> list[dict]:
    """Read data/knowledge_base/*.md into whole-file {'title','content','source'}
    docs, using the filename (title-cased) as the title. Missing directory -> []."""
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
        docs.append({"title": title, "content": content, "source": title})
    return docs


_H3_RE = re.compile(r"^###\s+(.+?)\s*$")
_MIN_PIECE_CHARS = 300


def _split_long(body: str, max_chars: int) -> list[str]:
    """Split an over-long section at '###' boundaries (else paragraphs).
    '###' subsections stay separate passages unless tiny (< 300 chars, merged
    into the previous one); anything still too long is hard-cut."""
    if len(body) <= max_chars:
        return [body]
    parts = re.split(r"\n(?=###\s)", body)
    if len(parts) == 1:
        parts = body.split("\n\n")
    pieces: list[str] = []
    for part in parts:
        if pieces and (len(part) < _MIN_PIECE_CHARS or len(pieces[-1]) < _MIN_PIECE_CHARS) \
                and len(pieces[-1]) + len(part) + 1 <= max_chars:
            pieces[-1] = f"{pieces[-1]}\n{part}"
        else:
            pieces.append(part)
    out: list[str] = []
    for piece in pieces:
        while len(piece) > max_chars:
            out.append(piece[:max_chars])
            piece = piece[max_chars:]
        out.append(piece)
    return [p.strip() for p in out if p.strip()]


def _piece_heading(piece: str) -> str | None:
    """The '###' heading that opens (or first appears in) a passage."""
    for line in piece.splitlines():
        m = _H3_RE.match(line)
        if m:
            return m.group(1)
    return None


def chunk_markdown(source: str, text: str, max_chars: int = _MAX_CHUNK_CHARS) -> list[dict]:
    """Split one Markdown document into passages at '## ' headings (ignoring
    '#' lines inside code fences). Each chunk is titled '<source> > <heading>'
    and remembers its source document."""
    chunks: list[dict] = []

    def emit(heading: str | None, body: str) -> None:
        body = body.strip()
        if len(body) < 40:
            return
        title = f"{source} > {heading}" if heading else source
        pieces = _split_long(body, max_chars)
        for i, piece in enumerate(pieces):
            if len(pieces) == 1:
                piece_title = title
            else:
                sub = _piece_heading(piece)
                piece_title = f"{title} > {sub}" if sub else f"{title} (part {i + 1})"
            chunks.append({"title": piece_title, "content": piece, "source": source})

    heading: str | None = None
    buf: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        match = None if in_fence else _H2_RE.match(line)
        if match:
            emit(heading, "\n".join(buf))
            heading, buf = match.group(1), [line]
        else:
            buf.append(line)
    emit(heading, "\n".join(buf))
    return chunks


def _chunked_markdown_kb_docs() -> list[dict]:
    chunks: list[dict] = []
    for doc in _load_markdown_whole_docs():
        chunks.extend(chunk_markdown(doc["source"], doc["content"]))
    return chunks


for _doc in EMBEDDED_KB_DOCS:
    _doc.setdefault("source", _doc["title"])

# Whole documents (embedded snippets + full Markdown files): used only to
# reproduce the pre-chunking baseline in `eval/`.
WHOLE_KB_DOCS: list[dict] = EMBEDDED_KB_DOCS + _load_markdown_whole_docs()

# Default search corpus: embedded snippets + heading-level chunks of the
# runbook Markdown files, built once at import time.
KB_DOCS: list[dict] = EMBEDDED_KB_DOCS + _chunked_markdown_kb_docs()


# ── Tokenisation ──────────────────────────────────────────────────────────

_CAMEL_ACRONYM = re.compile(r"([A-Z]+)([A-Z][a-z])")
_CAMEL_WORD = re.compile(r"([a-z0-9])([A-Z])")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*")
_STOPWORDS = frozenset(
    """
    the and for are was were been being has have had having not nor but with without from into onto over under
    again further once about above below out off per via also just only own same such both each few more most
    other some any all can could should would may might will shall does did done this that these those there
    here its our your their them his her you they she him who whom what when where which while than too very
    then else info debug trace warn
    name namespace state changed average identifier
    """.split()
)
_SUFFIXES = ("ations", "ation", "ions", "ion", "ings", "ing", "ed", "s")


def _stem(token: str) -> str:
    """Light, consistent suffix stripping (applied to both KB text and queries,
    so only consistency matters, not linguistic correctness)."""
    if token.endswith("ss"):
        return token
    if token.endswith("ies") and len(token) > 5:
        return token[:-3] + "y"
    for suffix in _SUFFIXES:
        min_stem = 3 if suffix == "s" else 4     # "pods" -> "pod", but never mangle short stems
        if token.endswith(suffix) and len(token) - len(suffix) >= min_stem:
            token = token[: -len(suffix)]
            break
    if token.endswith("e") and len(token) > 4:
        token = token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    """Lower-case content words: splits camelCase/dotted identifiers, drops
    stopwords, numbers and 1-2 letter tokens, and applies a light stemmer."""
    text = _CAMEL_ACRONYM.sub(r"\1 \2", text)
    text = _CAMEL_WORD.sub(r"\1 \2", text)
    tokens = []
    for word in _WORD_RE.findall(text):
        word = word.lower()
        if len(word) < 3 or word in _STOPWORDS:
            continue
        tokens.append(_stem(word))
    return tokens


def _doc_tokens(doc: dict) -> list[str]:
    # Headings are strong signals: count title tokens twice.
    title = tokenize(doc["title"])
    return title + title + tokenize(doc["content"])


# ── BM25 ranking ──────────────────────────────────────────────────────────

_K1, _B = 1.5, 0.75
_NO_MATCH = "No relevant knowledge base documents found for this query."
_default_index: list[list[str]] | None = None


def _bm25_scores(query_tokens: set[str], docs_tokens: list[list[str]]) -> list[float]:
    n = len(docs_tokens)
    if n == 0:
        return []
    avgdl = (sum(len(d) for d in docs_tokens) / n) or 1.0
    df: Counter = Counter()
    for tokens in docs_tokens:
        df.update(set(tokens))
    scores: list[float] = []
    for tokens in docs_tokens:
        tf = Counter(tokens)
        dl = len(tokens) or 1
        score = 0.0
        for term in query_tokens:
            freq = tf.get(term, 0)
            if not freq:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            score += idf * (freq * (_K1 + 1)) / (freq + _K1 * (1 - _B + _B * dl / avgdl))
        scores.append(score)
    return scores


def retrieve(
    query: str,
    documents: list[dict] | None = None,
    top_k: int = 3,
    max_per_source: int = 2,
    min_relative_score: float = 0.3,
) -> list[dict]:
    """Rank KB passages for `query` with BM25. Returns up to `top_k`
    {'title','source','content','score'} dicts, keeping at most
    `max_per_source` passages per source document and dropping passages
    scoring below `min_relative_score` x the best score."""
    global _default_index
    if not query or (documents is not None and not documents):
        return []

    query_tokens = set(tokenize(query))
    if not query_tokens:
        return []

    if documents is None:
        documents = KB_DOCS
        if _default_index is None:
            _default_index = [_doc_tokens(d) for d in KB_DOCS]
        docs_tokens = _default_index
    else:
        docs_tokens = [_doc_tokens(d) for d in documents]

    scores = _bm25_scores(query_tokens, docs_tokens)
    ranked = sorted(
        ((score, idx) for idx, score in enumerate(scores) if score > 0),
        key=lambda pair: (-pair[0], pair[1]),
    )
    if not ranked:
        return []

    best = ranked[0][0]
    per_source: Counter = Counter()
    hits: list[dict] = []
    for score, idx in ranked:
        if score < best * min_relative_score:
            break
        doc = documents[idx]
        source = doc.get("source", doc["title"])
        if per_source[source] >= max_per_source:
            continue
        per_source[source] += 1
        hits.append({"title": doc["title"], "source": source, "content": doc["content"], "score": score})
        if len(hits) >= top_k:
            break
    return hits


def keyword_search(
    query: str,
    documents: list[dict] | None = None,
    top_k: int = 3,
    max_chars: int = 1500,
) -> str:
    """BM25 retrieval formatted for prompts: '[<passage title>]\\n<text>'
    blocks separated by '---'. Each title doubles as the citation label."""
    hits = retrieve(query, documents=documents, top_k=top_k)
    if not hits:
        return _NO_MATCH
    blocks = []
    for hit in hits:
        content = hit["content"]
        if len(content) > max_chars:
            content = content[:max_chars].rstrip() + " ..."
        blocks.append(f"[{hit['title']}]\n{content}")
    return "\n\n---\n\n".join(blocks)


# ── Query construction ────────────────────────────────────────────────────

_SIGNAL_RE = re.compile(
    r"(?i)\b(error|exception|fatal|fail(?:ed|ure|ing|s)?|refused|time[d ]?[- ]?out|timeout|exhaust\w*|oom\w*|"
    r"out of memory|killed|crashloop\w*|back-?off|deadlock\w*|lag|unavailable|denied|unauthori[sz]ed|throttl\w*|"
    r"alarm|too many|no space|expire[sd]?|threshold|stale|rejected|panic|segfault|5\d\d)\b"
)
_LOG_PREFIX_RE = re.compile(
    r"^\s*(?:\[?\d{4}[-/]\d{2}[-/]\d{2}[T ][\d:.,]+Z?\]?|\w{3}\s+\d+\s+[\d:]+)\s*"
)
_MD_NOISE = re.compile(r"[#*`>_]+")


def _signature_lines(raw_logs: str, limit: int = 10, width: int = 220) -> list[str]:
    """The log lines that carry the failure evidence: error/failure-signal
    lines, padded with the remaining lines when fewer than 3 are found
    (timestamp prefix removed, near-duplicates and injected instructions dropped)."""
    seen: set[str] = set()
    signal: list[str] = []
    other: list[str] = []
    for line in raw_logs.splitlines():
        line = line.strip()
        if not line or looks_like_injection(line):   # never let embedded instructions steer retrieval
            continue
        has_signal = bool(_SIGNAL_RE.search(line))
        line = _LOG_PREFIX_RE.sub("", line)[:width]
        key = re.sub(r"\d+", "#", line.lower())
        if key in seen:
            continue
        seen.add(key)
        (signal if has_signal else other).append(line)
    # plenty of explicit failure lines -> use only those; otherwise pad with context lines
    return (signal if len(signal) >= 3 else signal + other)[:limit]


def _summary_excerpt(summary: str, limit: int = 300) -> str:
    text = _MD_NOISE.sub(" ", summary or "")
    match = re.search(r"(?i)executive summary", text)
    if match:
        text = text[match.end():]
    return re.sub(r"\s+", " ", text).strip()[:limit]


def build_rag_query(
    log_type: str,
    critical_issues: list | None,
    log_summary: str,
    raw_logs: str,
) -> str:
    """Query text for the knowledge-base search, built from the incident's own
    evidence: issue titles, the error lines from the raw log, and the body of
    the executive summary (not the report heading)."""
    parts: list[str] = []
    if log_type and log_type not in ("other", "mixed", "unknown"):
        parts.append(log_type)
    for issue in (critical_issues or [])[:3]:
        parts.append(str(issue.get("title", issue)) if isinstance(issue, dict) else str(issue))
    parts.extend(_signature_lines(raw_logs or ""))
    excerpt = _summary_excerpt(log_summary)
    if excerpt:
        parts.append(excerpt)
    return " ".join(parts)[:2000]


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
