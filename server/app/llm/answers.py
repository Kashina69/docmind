from app.llm.client import _call_llm
from app.llm.prompts import build_direct_prompt, build_rag_prompt, strip_think_tags


def generate_answer(
    query:          str,
    context_chunks: list[dict],
    history:        list[dict],
    style:          str = "explanatory",
    model:          str | None = None,
    role:           str = "rag",
) -> str:
    prompt = build_rag_prompt(query, context_chunks, history, style)

    n_docs = len({c["metadata"].get("filename") for c in context_chunks if c.get("metadata")})
    role = role or "rag"
    print(f"[LLM:{role}] RAG answer: '{query[:80]}' | {len(context_chunks)} chunks, {n_docs} doc(s)")

    raw    = _call_llm(messages=[{"role": "user", "content": prompt}],
                       max_tokens=4096, temperature=0.5, role=role, model=model)
    answer = strip_think_tags(raw)
    print(f"[LLM:{role}] Answer: {len(answer)} chars")
    return answer


def direct_answer(
    query:   str,
    history: list[dict],
    style:   str = "explanatory",
    model:   str | None = None,
    role:    str = "rag",
) -> str:
    print(f"[LLM:{role}] Direct answer: '{query[:80]}'")

    prompt = build_direct_prompt(query, history, style)
    raw    = _call_llm(messages=[{"role": "user", "content": prompt}],
                       max_tokens=1024, temperature=0.5, role=role, model=model)
    answer = strip_think_tags(raw)
    print(f"[LLM:{role}] Direct: {len(answer)} chars")
    return answer
