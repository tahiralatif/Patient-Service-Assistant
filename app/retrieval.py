"""Finds the knowledge-base chunks that answer a question, and returns
NOTHING when no chunk is relevant enough. Returning nothing is what lets
the assistant escalate instead of guessing.
"""
import math
import re
from dataclasses import dataclass

from app.kb import Chunk, load_chunks

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "be", "do", "does", "did", "i",
    "my", "me", "we", "you", "your", "to", "of", "in", "on", "at", "for",
    "and", "or", "what", "which", "who", "when", "where", "how", "can",
    "could", "should", "will", "there", "it", "this", "that", "about",
    "please", "tell", "need", "want", "have", "has", "with", "any",
}

# A chunk must cover at least this share of the question's meaning
# (weighted by word rarity). Tune it by looking at real scores.
MIN_COVERAGE = 0.5
TOP_K = 3


def _tokens(text: str) -> list[str]:
    # Crude stemming: keep the first 6 letters, so "prepare" and
    # "preparation" both become "prepar".
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w[:6] for w in words if w not in STOPWORDS and len(w) > 1]


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float  # 0..1, share of the question covered by this chunk


class Retriever:
    def __init__(self, chunks: list[Chunk] | None = None) -> None:
        self.chunks = chunks if chunks is not None else load_chunks()
        self._docs = [
            set(_tokens(f"{c.title} {c.section} {c.text}")) for c in self.chunks
        ]
        self._n = len(self._docs)
        self._df: dict[str, int] = {}
        for words in self._docs:
            for w in words:
                self._df[w] = self._df.get(w, 0) + 1

    def _idf(self, word: str) -> float:
        # Rare words weigh more. A word found in no chunk is the rarest.
        df = self._df.get(word, 0.5)
        return math.log(1 + self._n / df)

    def search(self, query: str) -> list[Hit]:
        q_words = set(_tokens(query))
        if not q_words:
            return []

        total = sum(self._idf(w) for w in q_words)
        hits: list[Hit] = []
        for chunk, words in zip(self.chunks, self._docs):
            matched = sum(self._idf(w) for w in q_words if w in words)
            coverage = matched / total
            if coverage >= MIN_COVERAGE:
                hits.append(Hit(chunk=chunk, score=round(coverage, 3)))

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:TOP_K]