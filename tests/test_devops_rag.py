from devops_rag import EMBEDDED_KB_DOCS, keyword_search, search_knowledge_base


def test_embedded_kb_docs_have_required_shape():
    assert len(EMBEDDED_KB_DOCS) >= 5
    for doc in EMBEDDED_KB_DOCS:
        assert doc["title"]
        assert len(doc["content"]) > 50
    titles = " ".join(d["title"].lower() for d in EMBEDDED_KB_DOCS)
    assert "kubernetes" in titles or "k8s" in titles
    assert "redis" in titles
    severity_doc = next(d for d in EMBEDDED_KB_DOCS if "severity" in d["title"].lower())
    assert "p1" in severity_doc["content"].lower()


def test_keyword_search_empty_query_or_docs():
    assert "No relevant" in keyword_search("")
    assert "No relevant" in keyword_search("kubernetes", documents=[])


def test_keyword_search_is_case_insensitive_and_ranks_by_score():
    docs = [
        {"title": "A", "content": "kubernetes pod crash restart"},
        {"title": "B", "content": "kubernetes pod crash restart kubernetes kubernetes"},
        {"title": "C", "content": "totally unrelated nginx content"},
    ]
    result = keyword_search("KUBERNETES POD", documents=docs, top_k=2)
    assert result.index("[B]") < result.index("[A]")
    assert "[C]" not in result


def test_keyword_search_top_k_bounds_result_count():
    docs = [{"title": f"D{i}", "content": "kubernetes issue"} for i in range(5)]
    result = keyword_search("kubernetes", documents=docs, top_k=2)
    assert result.count("---") == 1  # 2 results joined by exactly one separator


def test_search_knowledge_base_without_query_engine_uses_keyword_fallback():
    result = search_knowledge_base("redis connection pool", query_engine=None)
    assert "Redis" in result


def test_search_knowledge_base_uses_working_query_engine_verbatim():
    calls = []

    class FakeEngine:
        def query(self, q):
            calls.append(q)
            return "engine says: use pgbouncer"

    result = search_knowledge_base("postgres connections", query_engine=FakeEngine())
    assert result == "engine says: use pgbouncer"
    assert calls == ["postgres connections"]


def test_search_knowledge_base_falls_back_on_raising_query_engine():
    class RaisingEngine:
        def query(self, q):
            raise RuntimeError("index unavailable")

    result = search_knowledge_base("redis pool exhaustion", query_engine=RaisingEngine())
    assert "Redis" in result


def test_search_knowledge_base_falls_back_on_empty_query_engine_result():
    class EmptyEngine:
        def query(self, q):
            return "   "

    result = search_knowledge_base("redis pool exhaustion", query_engine=EmptyEngine())
    assert "Redis" in result
