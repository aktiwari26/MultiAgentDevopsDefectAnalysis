"""The original keyword scorer, kept only as a baseline for retrieval comparisons.

Score = number of whitespace-separated query tokens that appear (as substrings,
case-insensitive) anywhere in a document; whole documents are returned. This is
what devops_rag.keyword_search did before the BM25/chunking rewrite. Do not use
it in the pipeline; `python -m eval.run_eval --scorer legacy` reproduces the
"before" numbers in the README.
"""


def legacy_search(query: str, documents: list[dict], top_k: int = 3) -> list[dict]:
    query_tokens = [t.lower() for t in query.split() if t]
    scored = []
    for doc in documents:
        content_lower = doc["content"].lower()
        score = sum(1 for token in query_tokens if token in content_lower)
        if score > 0:
            scored.append((score, doc["title"], doc))
    scored.sort(key=lambda s: (s[0], s[1]), reverse=True)
    return [d for _, _, d in scored[:top_k]]
