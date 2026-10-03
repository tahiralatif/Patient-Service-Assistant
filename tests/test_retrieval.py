from app.retrieval import Retriever


def test_finds_specialty_section():
    hits = Retriever().search("How do I prepare for my cardiology appointment?")
    assert hits
    assert hits[0].chunk.section == "Cardiology"


def test_finds_opening_days():
    hits = Retriever().search("Is the clinic open on Friday?")
    assert hits
    assert hits[0].chunk.doc_id == "hours_and_booking"


def test_unknown_topic_returns_nothing():
    # No parking document exists on purpose.
    assert Retriever().search("Where is the clinic parking?") == []

def test_medical_records_question_is_not_answered_from_kb():
    assert Retriever().search("Can the doctor see my medical records?") == []