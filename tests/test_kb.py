from app.kb import KB_DIR, load_chunks


def test_loads_chunks_from_all_searchable_docs():
    chunks = load_chunks()
    doc_ids = {c.doc_id for c in chunks}
    assert {
        "preparation_instructions",
        "rescheduling_and_cancellation",
        "hours_and_booking",
        "insurance_general",
    } <= doc_ids
    assert len(chunks) >= 8


def test_chunk_ids_are_unique():
    chunks = load_chunks()
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))


def test_every_kb_file_is_loaded():
    # Catches a file silently skipped (e.g. searchable: false by mistake).
    loaded = {c.doc_id for c in load_chunks()}
    assert len(loaded) == len(list(KB_DIR.glob("*.md")))