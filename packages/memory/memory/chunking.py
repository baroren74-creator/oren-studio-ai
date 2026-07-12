"""Text chunking — docs/decisions.md ADR-002's "~300 line" custom layer,
not a RAG framework's chunker. Deliberately simple: word-count-based
with overlap, not token-aware (no tokenizer dependency). Good enough for
this project's known, bounded source types (GitHub READMEs/digests,
YouTube transcripts — see agents/research_agent) — revisit only if a
real source turns out to need smarter (e.g. sentence-boundary-aware)
splitting.
"""

from __future__ import annotations

DEFAULT_CHUNK_WORDS = 200
DEFAULT_OVERLAP_WORDS = 40


def chunk_text(
    text: str, *, chunk_words: int = DEFAULT_CHUNK_WORDS, overlap_words: int = DEFAULT_OVERLAP_WORDS
) -> list[str]:
    """Split `text` into overlapping word-count chunks.

    Overlap exists so a fact split across a chunk boundary still appears
    whole in at least one chunk — cheap insurance against the most
    common way naive chunking loses context, at the cost of some
    duplicate embedding work (acceptable at this project's scale).
    """
    if chunk_words <= 0:
        raise ValueError("chunk_words must be positive")
    if overlap_words < 0 or overlap_words >= chunk_words:
        raise ValueError("overlap_words must be >= 0 and < chunk_words")

    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    step = chunk_words - overlap_words
    for start in range(0, len(words), step):
        chunk_slice = words[start : start + chunk_words]
        if not chunk_slice:
            break
        chunks.append(" ".join(chunk_slice))
        if start + chunk_words >= len(words):
            break

    return chunks
