"""Tests pour le parser JSON robuste."""

import pytest

from frenchlaw_bench.json_utils import parse_llm_json


def test_valid_json():
    assert parse_llm_json('{"a": 1}') == {"a": 1}


def test_trailing_comma_object():
    assert parse_llm_json('{"a": 1, "b": 2,}') == {"a": 1, "b": 2}


def test_trailing_comma_array():
    assert parse_llm_json('{"items": [1, 2, 3,]}') == {"items": [1, 2, 3]}


def test_trailing_comma_nested():
    text = '{"satisfied": true, "evidence": ["quote1", "quote2",], "confidence": 0.9,}'
    result = parse_llm_json(text)
    assert result["satisfied"] is True
    assert result["evidence"] == ["quote1", "quote2"]
    assert result["confidence"] == 0.9


def test_markdown_block():
    text = '```json\n{"a": 1}\n```'
    assert parse_llm_json(text) == {"a": 1}


def test_markdown_block_with_trailing_comma():
    text = '```json\n{"a": 1, "b": 2,}\n```'
    assert parse_llm_json(text) == {"a": 1, "b": 2}


def test_text_before_json():
    text = 'Here is my response:\n{"a": 1}'
    assert parse_llm_json(text) == {"a": 1}


def test_text_after_json():
    text = '{"a": 1}\nEnd of response.'
    assert parse_llm_json(text) == {"a": 1}


def test_text_around_json():
    text = 'Result:\n{"satisfied": true, "reasoning": "ok"}\nDone.'
    result = parse_llm_json(text)
    assert result["satisfied"] is True


def test_array_json():
    text = '[{"claim": "test"}]'
    result = parse_llm_json(text)
    assert isinstance(result, list)
    assert result[0]["claim"] == "test"


def test_array_with_trailing_comma():
    text = '[{"a": 1}, {"b": 2},]'
    result = parse_llm_json(text)
    assert len(result) == 2


def test_invalid_json_raises():
    with pytest.raises(Exception):
        parse_llm_json("not json at all")


def test_markdown_block_no_lang():
    text = '```\n{"a": 1}\n```'
    assert parse_llm_json(text) == {"a": 1}


def test_multiple_trailing_commas():
    text = '{"a": [1, 2,], "b": {"c": 3,},}'
    result = parse_llm_json(text)
    assert result == {"a": [1, 2], "b": {"c": 3}}
