"""Decides whether an answer may be shown as a verified fact.
Rule: an answer is grounded only if it cites at least one source AND
every cited source was actually retrieved for this question.
Anything else is replaced by a safe 'not found' reply.
"""
from dataclasses import dataclass, field

from app.retrieval import Hit, Retriever

NOT_FOUND_REPLY = (
    "I don't have verified information on that, so I won't guess. "
    "I've passed your question to our team."
)


@dataclass(frozen=True)
class GroundedAnswer:
    grounded: bool
    reply: str
    sources: list[str] = field(default_factory=list)


def verify_citations(cited_ids: list[str], hits: list[Hit]) -> bool:
    allowed = {h.chunk.chunk_id for h in hits}
    return bool(cited_ids) and set(cited_ids) <= allowed


def ground(reply: str, cited_ids: list[str], hits: list[Hit]) -> GroundedAnswer:
    """Check a (later: LLM-written) reply against what was retrieved."""
    if not verify_citations(cited_ids, hits):
        return GroundedAnswer(grounded=False, reply=NOT_FOUND_REPLY)
    return GroundedAnswer(grounded=True, reply=reply, sources=sorted(set(cited_ids)))


def answer_from_kb(query: str, retriever: Retriever) -> GroundedAnswer:
    """No-LLM answer: return the best chunk's own text, with its source.
    Quoting the chunk cannot invent anything, so this is always grounded.
    """
    hits = retriever.search(query)
    if not hits:
        return GroundedAnswer(grounded=False, reply=NOT_FOUND_REPLY)
    best = hits[0].chunk
    return GroundedAnswer(grounded=True, reply=best.text, sources=[best.chunk_id])