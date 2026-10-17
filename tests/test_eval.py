"""Guards for the evaluation set and the retrieval-quality floor it measures."""
import argparse

import pytest

from devops_rag import KB_DOCS
from eval.cases import CASES
from eval.run_eval import run_offline

LOG_TYPES = {"kubernetes", "nginx", "cloudwatch", "application", "database", "mixed", "other"}


def _offline(scorer="bm25", k=3):
    return run_offline(argparse.Namespace(scorer=scorer, k=k, ids=None, limit=None, verbose=False))


def test_cases_are_well_formed_and_unique():
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids)) >= 20
    for c in CASES:
        assert c["log"].strip()
        assert c["severity"] in {"P1", "P2", "P3", "P4"}
        assert c["log_type"] in LOG_TYPES
        assert isinstance(c["expected_sources"], list) and isinstance(c["rca_keywords"], list)


def test_expected_sources_exist_in_the_knowledge_base():
    sources = {d["source"] for d in KB_DOCS}
    for c in CASES:
        for entry in c["expected_sources"]:
            source, _, heading = entry.partition("::")
            assert source in sources, f"{c['id']}: unknown source {source!r}"
            if heading:
                assert any(d["source"] == source and heading.lower() in d["title"].lower() for d in KB_DOCS), \
                    f"{c['id']}: no passage of {source!r} has a heading containing {heading!r}"


def test_the_set_covers_every_severity_and_the_injection_scenario():
    assert {c["severity"] for c in CASES} == {"P1", "P2", "P3", "P4"}
    assert any("forbidden_severity" in c for c in CASES)


def test_retrieval_quality_floor():
    result = _offline()
    assert result["retrieval_cases"] >= 15
    assert result["passage_recall@3"] >= 0.90
    assert result["passage_recall@1"] >= 0.70
    assert result["avg_context_chars"] < 5000
    assert result["top1_is_catch_all_playbooks"] <= 0.5


def test_bm25_returns_far_less_context_than_the_legacy_whole_document_scorer():
    new, old = _offline("bm25"), _offline("legacy")
    assert new["avg_context_chars"] * 3 < old["avg_context_chars"]
    assert new["top1_is_catch_all_playbooks"] < old["top1_is_catch_all_playbooks"]
