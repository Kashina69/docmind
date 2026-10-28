from app.supabase_client import get_service_client
from app.rate_limiter    import acquire_task_token
from app.llm             import generate_json
from app.jobs            import write_result
from app.sources         import fetch_source_content

MAX_FLASHCARDS = 20


def generate_flashcards(
    job_id:          str,
    user_id:         str,
    conversation_id: str | None,
    document_id:     str | None,
    r,
) -> None:
    if not conversation_id and not document_id:
        write_result(r, job_id, {
            "status":  "error",
            "message": "Either conversation_id or document_id is required",
        })
        return

    supabase = get_service_client()
    source_content, source_type, source_id = fetch_source_content(
        supabase, user_id, conversation_id, document_id
    )

    if not source_content:
        write_result(r, job_id, {
            "status":  "error",
            "message": "No content found to generate flashcards from",
        })
        return

    print(f"[Flashcards] source_type={source_type} id={source_id} "
          f"content_len={len(source_content)}")

    acquired = acquire_task_token(r)
    if not acquired:
        raise Exception("RATE_LIMIT_WAIT")

    cards = generate_json([
        {
            "role":    "system",
            "content": (
                f"Generate up to {MAX_FLASHCARDS} flashcards from the content below. "
                "Return ONLY a JSON array — no explanation, no markdown. "
                'Each item must have exactly two keys: "question" and "answer". '
                "Questions should test key concepts. Answers should be concise (1-3 sentences).\n\n"
                'Example format: [{"question": "What is X?", "answer": "X is ..."}]'
            ),
        },
        {
            "role":    "user",
            "content": source_content,
        },
    ])

    valid_cards = [
        c for c in cards
        if isinstance(c, dict)
        and isinstance(c.get("question"), str) and c["question"].strip()
        and isinstance(c.get("answer"),   str) and c["answer"].strip()
    ]

    if not valid_cards:
        write_result(r, job_id, {
            "status":  "error",
            "message": "LLM returned no valid flashcards",
        })
        return

    deck_id = _persist_flashcards(
        supabase, user_id, source_type, conversation_id, document_id, valid_cards
    )

    write_result(r, job_id, {
        "status":  "done",
        "deck_id": deck_id,
        "count":   len(valid_cards),
    })

    print(f"[Flashcards] deck={deck_id} created with {len(valid_cards)} cards")


def _persist_flashcards(
    supabase,
    user_id:         str,
    source_type:     str,
    conversation_id: str | None,
    document_id:     str | None,
    cards:           list[dict],
) -> str:
    deck_result = supabase.schema("rag").table("flashcard_decks").insert({
        "user_id":         user_id,
        "source_type":     source_type,
        "conversation_id": conversation_id,
        "document_id":     document_id,
        "title":           "Flashcard Deck",
    }).execute()

    deck_id = deck_result.data[0]["id"]

    supabase.schema("rag").table("flashcards").insert([
        {
            "deck_id":  deck_id,
            "question": c["question"].strip(),
            "answer":   c["answer"].strip(),
        }
        for c in cards
    ]).execute()

    return deck_id
