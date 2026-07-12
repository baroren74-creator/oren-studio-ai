from __future__ import annotations

import pytest

from memory.chunking import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_short_text_returns_a_single_chunk():
    text = "one two three four five"
    assert chunk_text(text, chunk_words=10, overlap_words=2) == [text]


def test_long_text_splits_with_overlap():
    words = [f"w{i}" for i in range(1, 21)]  # w1..w20
    text = " ".join(words)

    # step = chunk_words - overlap_words = 7, so chunk starts land at 0, 7, 14
    chunks = chunk_text(text, chunk_words=10, overlap_words=3)

    assert len(chunks) == 3
    assert chunks[0] == " ".join(words[0:10])
    # each next chunk starts overlap_words back from where the previous ended
    assert chunks[1] == " ".join(words[7:17])
    assert chunks[2] == " ".join(words[14:20])


def test_no_word_is_dropped_across_chunk_boundaries():
    words = [f"w{i}" for i in range(1, 51)]
    text = " ".join(words)

    chunks = chunk_text(text, chunk_words=12, overlap_words=4)

    covered: set[str] = set()
    for chunk in chunks:
        covered.update(chunk.split())
    assert covered == set(words)


def test_rejects_non_positive_chunk_words():
    with pytest.raises(ValueError):
        chunk_text("hello world", chunk_words=0)


def test_rejects_overlap_not_smaller_than_chunk_words():
    with pytest.raises(ValueError):
        chunk_text("hello world", chunk_words=10, overlap_words=10)
    with pytest.raises(ValueError):
        chunk_text("hello world", chunk_words=10, overlap_words=-1)
