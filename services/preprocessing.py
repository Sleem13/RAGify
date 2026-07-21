"""Lightweight, dependency-free text normalization for lexical retrieval."""

from __future__ import annotations

import re


_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "he",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "that",
    "the",
    "to",
    "was",
    "were",
    "will",
    "with",
}
_PROTECTED_NEGATIONS = {"no", "not", "nor", "never"}
_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


def _simple_lemma(token: str) -> str:
    """Apply conservative English suffix normalization without NLTK downloads."""
    if not token.isascii():
        return token
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("ing") and len(token) > 5:
        base = token[:-3]
        if len(base) > 2 and base[-1] == base[-2]:
            base = base[:-1]
        return base
    if token.endswith("ed") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and not token.endswith("ss") and len(token) > 3:
        return token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    """Normalize text while retaining negation and non-English words."""
    clean_text = _URL_RE.sub(" ", text.casefold())
    tokens = _TOKEN_RE.findall(clean_text)
    return [
        _simple_lemma(token)
        for token in tokens
        if token not in _STOP_WORDS or token in _PROTECTED_NEGATIONS
    ]


def preprocess_text(text: str) -> str:
    return " ".join(tokenize(text))
