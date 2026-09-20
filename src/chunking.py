from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []

        # Split using regex that matches sentence endings followed by whitespace or end of string
        # Matches: .  , !  , ?  , .\n, !\n, ?\n, etc.
        # Keep the delimiter as part of the sentence
        sentence_enders = r'(?<=[.!?])\s+|(?<=[.!?])\n'
        sentences = re.split(sentence_enders, text)

        # Filter out empty strings that may result from splitting
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            # Fallback to single chunk if no sentences detected
            return [text]

        chunks: list[str] = []
        current_chunk_sentences: list[str] = []

        for sentence in sentences:
            current_chunk_sentences.append(sentence)
            if len(current_chunk_sentences) >= self.max_sentences_per_chunk:
                chunks.append(" ".join(current_chunk_sentences))
                current_chunk_sentences = []

        # Add any remaining sentences as the last chunk
        if current_chunk_sentences:
            chunks.append(" ".join(current_chunk_sentences))

        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        return self._split(text, list(self.separators))

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        if len(current_text) <= self.chunk_size:
            return [current_text]

        if not remaining_separators:
            # Fallback: split by character count if no separators left
            return [current_text[i:i + self.chunk_size] for i in range(0, len(current_text), self.chunk_size)]

        current_separator = remaining_separators[0]
        next_separators = remaining_separators[1:]

        # Split using the current separator
        parts = current_text.split(current_separator)

        chunks: list[str] = []

        for part in parts:
            if len(part) <= self.chunk_size:
                # If part is small enough, add it as a chunk
                chunks.append(part)
            else:
                # If part is too large, recursively split it
                # We add the separator back for the recursive split if it's a non-empty string
                # Note: for empty string separator '', we don't add it back
                separator_to_add = current_separator if current_separator != "" else ""
                sub_chunks = self._split(part + separator_to_add, next_separators)
                chunks.extend(sub_chunks)

        # Clean up any trailing separators from the last split if they ended up as empty strings
        # This can happen if the text ends with a separator
        chunks = [chunk for chunk in chunks if chunk]

        return chunks


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    if _dot(vec_a, vec_a) == 0 or _dot(vec_b, vec_b) == 0:
        return 0.0
    return _dot(vec_a, vec_b) / (math.sqrt(_dot(vec_a, vec_a)) * math.sqrt(_dot(vec_b, vec_b)))


class HeadingChunker:
    """
    Chunk markdown documents by headings (#, ##, ###).

    If a section is larger than chunk_size, fallback to recursive chunking,
    re-attaching the section heading to each sub-chunk for context preservation.
    """

    def __init__(self, chunk_size: int = 500) -> None:
        self.chunk_size = chunk_size
        self._recursive = RecursiveChunker(chunk_size=chunk_size)

    def chunk(self, text: str) -> list[str]:
        if not text.strip():
            return []

        heading_pattern = r"(?=(?:^|\n)#{1,6}\s+)"
        sections = re.split(heading_pattern, text)
        sections = [s.strip() for s in sections if s.strip()]

        if not sections:
            return self._recursive.chunk(text)

        chunks: list[str] = []
        for section in sections:
            if len(section) <= self.chunk_size:
                chunks.append(section)
            else:
                lines = section.split("\n", 1)
                heading = lines[0] if lines[0].startswith("#") else ""
                body = lines[1] if len(lines) > 1 else section

                sub_chunks = self._recursive.chunk(body)
                for sub in sub_chunks:
                    if heading and not sub.startswith("#"):
                        chunks.append(f"{heading}\n{sub}")
                    else:
                        chunks.append(sub)

        return chunks


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        fixed_size = FixedSizeChunker(chunk_size=chunk_size, overlap=20)
        sentence_chunker = SentenceChunker(max_sentences_per_chunk=3)
        recursive_chunker = RecursiveChunker(chunk_size=chunk_size)

        fixed_chunks = fixed_size.chunk(text)
        sentence_chunks = sentence_chunker.chunk(text)
        recursive_chunks = recursive_chunker.chunk(text)

        def _stats(chunks: list[str]) -> dict:
            count = len(chunks)
            avg_length = sum(len(c) for c in chunks) / count if count > 0 else 0.0
            return {
                "count": count,
                "avg_length": avg_length,
                "chunks": chunks,
            }

        return {
            "fixed_size": _stats(fixed_chunks),
            "by_sentences": _stats(sentence_chunks),
            "recursive": _stats(recursive_chunks),
        }
