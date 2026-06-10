from __future__ import annotations

import re

from phases.phase2_rag_core.chunking.tokenizer import Tokenizer


class TextSplitter:
    """Token-aware splitting with structure-aware boundaries."""

    def __init__(self, tokenizer: Tokenizer, max_tokens: int, overlap_tokens: int) -> None:
        self.tokenizer = tokenizer
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def split(self, text: str, content_type: str = "text") -> list[str]:
        if self.tokenizer.count(text) <= self.max_tokens:
            return [text]

        segments = self._segment_text(text, content_type)
        chunks: list[str] = []
        current = ""

        for segment in segments:
            candidate = f"{current}\n{segment}".strip() if current else segment
            if self.tokenizer.count(candidate) <= self.max_tokens:
                current = candidate
                continue

            if current:
                chunks.append(current)
                overlap = self._tail_overlap(current)
                current = f"{overlap}\n{segment}".strip() if overlap else segment
            else:
                if self.tokenizer.count(segment) > self.max_tokens:
                    chunks.extend(self._force_split(segment))
                    current = ""
                else:
                    current = segment

        if current:
            chunks.append(current)

        return chunks

    def _segment_text(self, text: str, content_type: str) -> list[str]:
        if content_type == "table":
            rows = [line for line in text.splitlines() if line.strip()]
            if rows:
                return rows

        for pattern in (r"\n##+ ", r"\n#+ ", r"\n\n+", r"(?<=\.)\s+"):
            parts = re.split(pattern, text)
            parts = [p.strip() for p in parts if p and p.strip()]
            if len(parts) > 1:
                return parts

        return [text]

    def _force_split(self, text: str) -> list[str]:
        if self.tokenizer.count(text) <= self.max_tokens:
            return [text]

        sentences = re.split(r"(?<=\.)\s+", text)
        if len(sentences) > 1:
            chunks: list[str] = []
            current = ""
            for sentence in sentences:
                candidate = f"{current} {sentence}".strip() if current else sentence
                if self.tokenizer.count(candidate) <= self.max_tokens:
                    current = candidate
                else:
                    if current:
                        chunks.append(current)
                    if self.tokenizer.count(sentence) > self.max_tokens:
                        chunks.extend(self._split_by_words(sentence))
                        current = ""
                    else:
                        current = sentence
            if current:
                chunks.append(current)
            return chunks

        return self._split_by_words(text)

    def _split_by_words(self, text: str) -> list[str]:
        words = text.split()
        chunks: list[str] = []
        current_words: list[str] = []

        for word in words:
            candidate = " ".join(current_words + [word])
            if self.tokenizer.count(candidate) <= self.max_tokens:
                current_words.append(word)
            else:
                if current_words:
                    chunks.append(" ".join(current_words))
                current_words = [word]

        if current_words:
            chunks.append(" ".join(current_words))
        return chunks

    def _tail_overlap(self, text: str) -> str:
        if self.overlap_tokens <= 0:
            return ""
        token_ids = self.tokenizer.encode(text)
        if len(token_ids) <= self.overlap_tokens:
            return text
        overlap_ids = token_ids[-self.overlap_tokens :]
        decoded = self.tokenizer.decode_tokens(overlap_ids)
        return decoded if decoded else text[-200:]
