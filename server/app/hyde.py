from app.embedder import embed_single_text, embed_texts
from app.llm import _call_llm
from app.prompts import strip_think_tags


def embed_query(query: str) -> list[float]:
    print(f"[HyDE] Embedding query directly (local model)")
    return embed_single_text(query)


def generate_hyde_embedding(query: str) -> tuple[list[float], str]:
    print(f"[HyDE] Generating hypothetical answer for: '{query[:80]}'")

    hypothetical_answer = _generate_hypothetical_answer(query)

    print(f"[HyDE] Hypothetical answer ({len(hypothetical_answer)} chars): "
          f"'{hypothetical_answer[:100]}'")

    embedding = embed_single_text(hypothetical_answer)

    return embedding, hypothetical_answer


def _generate_hypothetical_answer(query: str) -> str:
    hyde_prompt = f"""Write a textbook passage that teaches the following concept.
Include: what it is, how it works, and a concrete example.
Be specific and factual.

Question: {query}

Passage:"""

    try:
        raw = _call_llm(
            messages=[{"role": "user", "content": hyde_prompt}],
            max_tokens=300, temperature=0.7, role="hyde",
        )
    except Exception as e:
        print(f"[HyDE] Generation failed: {e} — falling back to direct query")
        return query

    cleaned = strip_think_tags(raw)

    if not cleaned:
        print(f"[HyDE] Empty after stripping think tags — falling back to direct query")
        return query

    return cleaned


def retrieve_hyde_candidate(query: str) -> list[float]:
    return embed_single_text(query)
