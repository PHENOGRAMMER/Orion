import pytest
from app.api.orion_llm_router import _clean, _is_acceptable


def test_clean_removes_leading_turn_tags_and_echoes():
    raw = "<|user_response|>\n[GRAPH CONTEXT] Symbol: utils.clamp.__doc__: Returns the smallest value..."
    cleaned = _clean(raw)
    assert not cleaned.startswith("<|user_response|>")
    assert not cleaned.startswith("[GRAPH CONTEXT]")


def test_is_acceptable_rejects_tag_and_context_echoes():
    raw_garbage = "<|user_response|>\n[GRAPH CONTEXT] Symbol: utils.clamp.__doc__: Returns the smallest value..."
    assert _is_acceptable(raw_garbage, "app.core.persistence.OrionPersistence") is False


def test_is_acceptable_accepts_valid_prose():
    good_answer = "OrionPersistence provides durable SQLite persistence for storing knowledge graph snapshots and scan metadata."
    assert _is_acceptable(good_answer, "app.core.persistence.OrionPersistence") is True
