from __future__ import annotations


class Tokenizer:
    """Token counting via tiktoken with character-based fallback."""

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        self._encoding = None
        self._encoding_name = encoding_name
        try:
            import tiktoken

            self._encoding = tiktoken.get_encoding(encoding_name)
        except Exception:  # noqa: BLE001
            self._encoding = None

    def count(self, text: str) -> int:
        if self._encoding is not None:
            return len(self._encoding.encode(text))
        return max(1, len(text) // 4)

    def decode_tokens(self, token_ids: list[int]) -> str:
        if self._encoding is not None:
            return self._encoding.decode(token_ids)
        return ""

    def encode(self, text: str) -> list[int]:
        if self._encoding is not None:
            return self._encoding.encode(text)
        return list(range(max(1, len(text) // 4)))
