from app.grounding import NOT_FOUND_REPLY, answer_from_kb, ground
from app.retrieval import Retriever


def test_known_question_is_grounded_with_source():
    result = answer_from_kb("How do I prepare for my cardiology appointment?", Retriever())
    assert result.grounded
    assert result.sources == ["preparation_instructions#Cardiology"]


def test_parking_is_not_grounded():
    result = answer_from_kb("Where is the clinic parking?", Retriever())
    assert not result.grounded
    assert result.reply == NOT_FOUND_REPLY


def test_invented_source_is_rejected():
    hits = Retriever().search("Is the clinic open on Friday?")
    result = ground("Parking is free.", ["parking_info#Free"], hits)
    assert not result.grounded


def test_reply_without_citation_is_rejected():
    hits = Retriever().search("Is the clinic open on Friday?")
    assert not ground("We are open Friday.", [], hits).grounded


def test_valid_citation_is_accepted():
    hits = Retriever().search("Is the clinic open on Friday?")
    cited = [hits[0].chunk.chunk_id]
    assert ground("The clinic is closed on Fridays.", cited, hits).grounded