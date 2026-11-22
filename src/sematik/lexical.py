"""Deterministic lexical retrieval for legacy identifiers (Discovery plane).

Lexical search proposes where to investigate; it never says what a field
means (ADR-0003, ADR-0006). Legacy schemas are dense with abbreviations
(``AV_LND_01``) where dense embeddings are weakest and exact tokens matter, so
this is the baseline every other retrieval method is measured against
(ADR-0006 section 10).

Everything here is pure and deterministic: no network, no randomness, ties
broken by document id, and a content digest for replay.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Sequence

TOKENIZER_VERSION = "ident-v1"

_NON_ALNUM = re.compile(r"[^0-9A-Za-z]+")
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_ALNUM_EDGE = re.compile(r"(?<=[A-Za-z])(?=[0-9])|(?<=[0-9])(?=[A-Za-z])")

STOPWORDS = frozenset({
    "a", "an", "the", "of", "for", "with", "or", "and", "to", "in", "by", "as",
    "is", "are", "its", "their", "that", "this", "on", "at", "from",
})


def _normalize(token: str) -> str:
    """Lowercase and strip one plural 's' (consistently on both sides)."""
    token = token.lower()
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        token = token[:-1]
    return token


def tokenize(text: str, *, keep_numeric: bool = False,
             drop_stopwords: bool = True) -> list[str]:
    """Split identifiers and prose into normalized tokens.

    ``AV_LND_01`` -> ``['av', 'lnd']``; ``LandAssessedValue`` ->
    ``['land', 'assessed', 'value']``. All-digit tokens are dropped by default
    (sequence suffixes such as ``_01`` carry no meaning).
    """
    tokens: list[str] = []
    for chunk in _NON_ALNUM.split(text):
        if not chunk:
            continue
        for part in _CAMEL.split(chunk):
            for sub in _ALNUM_EDGE.split(part):
                if not sub:
                    continue
                if sub.isdigit() and not keep_numeric:
                    continue
                token = _normalize(sub)
                if drop_stopwords and token in STOPWORDS:
                    continue
                tokens.append(token)
    return tokens


def _sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class Glossary:
    """Abbreviation -> expansion words, supplied by a Domain Pack.

    Glossary entries are domain knowledge and must be subject-matter-expert
    reviewed; they are query-side expansions that widen the search, never
    claims about meaning.
    """

    entries: Mapping[str, tuple[str, ...]]

    def __post_init__(self) -> None:
        normalized: dict[str, tuple[str, ...]] = {}
        for key, expansions in self.entries.items():
            key_tokens = tokenize(key, drop_stopwords=False)
            if len(key_tokens) != 1:
                raise ValueError(f"glossary key {key!r} must be a single token")
            words: list[str] = []
            for expansion in expansions:
                words.extend(tokenize(expansion))
            if not words:
                raise ValueError(f"glossary key {key!r} has no usable expansion")
            normalized[key_tokens[0]] = tuple(dict.fromkeys(words))
        object.__setattr__(self, "entries", MappingProxyType(normalized))

    def expansions_for(self, token: str) -> tuple[str, ...]:
        return self.entries.get(token, ())

    def digest(self) -> str:
        return _sha256({k: list(v) for k, v in sorted(self.entries.items())})


@dataclass(frozen=True)
class QueryAnalysis:
    tokens: tuple[str, ...]
    expansions: tuple[str, ...]          # added by the glossary, not in the query


@dataclass(frozen=True)
class LexicalHit:
    """One lexical candidate. ``score`` is a BM25 relevance score: ordinal
    evidence of resemblance, not a probability and not a Confidence."""

    doc_id: str
    score: float
    matched_terms: tuple[str, ...]
    expanded_terms: tuple[str, ...]      # matched only because of glossary expansion


class BM25Index:
    def __init__(self, documents: Mapping[str, str], *,
                 glossary: Glossary | None = None, k1: float = 1.5,
                 b: float = 0.75, expansion_weight: float = 0.5) -> None:
        if not documents:
            raise ValueError("a lexical index needs at least one document")
        if k1 <= 0 or not 0.0 <= b <= 1.0 or not 0.0 <= expansion_weight <= 1.0:
            raise ValueError("invalid BM25 parameters")
        for doc_id, text in documents.items():
            if not doc_id.strip() or not text.strip():
                raise ValueError("document ids and texts must be non-blank")
        self.documents: Mapping[str, str] = MappingProxyType(dict(documents))
        self.glossary = glossary
        self.k1, self.b, self.expansion_weight = k1, b, expansion_weight
        self._doc_ids = sorted(documents)
        self._tf = {d: Counter(tokenize(f"{d} {documents[d]}")) for d in self._doc_ids}
        self._len = {d: sum(c.values()) for d, c in self._tf.items()}
        self._avgdl = (sum(self._len.values()) / len(self._len)) or 1.0
        self._df: Counter[str] = Counter()
        for counts in self._tf.values():
            self._df.update(counts.keys())

    @property
    def size(self) -> int:
        return len(self._doc_ids)

    def params(self) -> dict[str, object]:
        return {"k1": self.k1, "b": self.b, "expansion_weight": self.expansion_weight,
                "glossary_digest": self.glossary.digest() if self.glossary else None,
                "tokenizer": TOKENIZER_VERSION}

    def digest(self) -> str:
        """Digest of corpus + parameters + glossary: identifies this index for replay."""
        return _sha256({"documents": dict(sorted(self.documents.items())),
                        "params": self.params()})

    def analyze(self, query: str) -> QueryAnalysis:
        tokens = tuple(dict.fromkeys(tokenize(query)))
        added: list[str] = []
        if self.glossary:
            for token in tokens:
                for word in self.glossary.expansions_for(token):
                    if word not in tokens and word not in added:
                        added.append(word)
        return QueryAnalysis(tokens=tokens, expansions=tuple(added))

    def _idf(self, term: str) -> float:
        n, df = len(self._doc_ids), self._df[term]
        return math.log(1.0 + (n - df + 0.5) / (df + 0.5))

    def search(self, query: str, *, k: int = 10) -> list[LexicalHit]:
        """Documents sharing at least one term with the (expanded) query.

        Documents with no overlap are never returned, so an unrelated query
        yields an empty list rather than a ranked list of noise."""
        if k <= 0:
            raise ValueError("k must be positive")
        analysis = self.analyze(query)
        weights = {t: 1.0 for t in analysis.tokens}
        weights.update({t: self.expansion_weight for t in analysis.expansions})
        hits: list[LexicalHit] = []
        for doc_id in self._doc_ids:
            counts, dl = self._tf[doc_id], self._len[doc_id]
            score, matched = 0.0, []
            for term, weight in weights.items():
                tf = counts.get(term, 0)
                if not tf or weight == 0.0:
                    continue
                norm = tf + self.k1 * (1 - self.b + self.b * dl / self._avgdl)
                score += weight * self._idf(term) * tf * (self.k1 + 1) / norm
                matched.append(term)
            if score > 0.0:
                expanded_only = tuple(sorted(t for t in matched if t in analysis.expansions))
                hits.append(LexicalHit(doc_id, score, tuple(sorted(matched)), expanded_only))
        hits.sort(key=lambda h: (-h.score, h.doc_id))
        return hits[:k]
