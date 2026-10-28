import re

from app.llm.client import _call_llm
from app.llm.prompts import format_history, strip_think_tags


def rewrite_query(query: str, history: list[dict]) -> str:
    if not history:
        return query

    words = set(re.findall(r"\b\w+\b", query.lower()))

    pronouns = {
        "it", "this", "that", "they", "them", "its",
        "these", "those", "he", "she",
    }

    vague_patterns = {"how", "why", "explain", "what", "tell"}

    is_short = len(query.split()) <= 10
    has_pronoun = bool(words & pronouns)
    is_vague = any(word in words for word in vague_patterns)

    if not (is_short or has_pronoun or is_vague):
        return query

    history = history[-3:]
    history_text = format_history(history)

    prompt = (
        "Rewrite the query into a complete, standalone search query.\n"
        "Resolve references using history. Keep meaning same.\n"
        "Output only the query.\n\n"
        f"{history_text}\n"
        f"Query: {query}\n"
        "Rewritten:"
    )

    raw = _call_llm(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=80, temperature=0.0, role="rewrite",
    )

    rewritten = strip_think_tags(raw).strip()

    if not rewritten or len(rewritten) > 200:
        return query

    print(f"[Rewrite] '{query[:50]}' -> '{rewritten[:50]}'")

    return rewritten


def needs_retrieval(query: str) -> bool:
    print(f"[Router] Checking if retrieval needed for: '{query[:80]}'")

    prompt = (
        "Does the following question require searching through "
        "uploaded documents to answer correctly?\n\n"
        "Answer YES if the question mentions 'my document', 'my PDF', "
        "'my notes', asks to summarise uploaded content, or references "
        "specific document content.\n"
        "Answer NO only for pure math, pure general knowledge, or greetings.\n\n"
        "Answer with only YES or NO.\n\n"
        f"Question: {query}\n\nAnswer:"
    )

    raw = _call_llm(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024, temperature=0.0, role="router",
    )

    yes_positions = [m.start() for m in re.finditer(r'\bYES\b', raw.upper())]
    no_positions  = [m.start() for m in re.finditer(r'\bNO\b',  raw.upper())]

    last_yes = yes_positions[-1] if yes_positions else -1
    last_no  = no_positions[-1]  if no_positions  else -1

    if last_yes == -1 and last_no == -1:
        result = True
    else:
        result = last_yes > last_no

    print(f"[Router] Retrieval needed: {result} (last YES pos={last_yes}, last NO pos={last_no})")

    return result


def route_generation_model(query: str, n_docs: int) -> str:
    fallback_role = "multi" if n_docs > 1 else "rag"
    print(f"[Router] Routing role for: '{query[:80]}' (n_docs={n_docs})")

    prompt = (
        "You are a routing classifier. Given a user query, decide which LLM role "
        "should handle it.\n\n"
        "Reply with ONLY the role name — no explanation, no punctuation.\n\n"
        "Roles:\n"
        "  rag — single-document tasks: summarise, explain a concept, "
        "find a section, extract dates/entities/requirements, list items, "
        "answer a factual question from one document\n"
        "  multi — cross-document tasks: compare documents, identify contradictions, "
        "gap analysis, compliance check across policies, research synthesis, "
        "find missing requirements across sources\n\n"
        f"Query: {query}\n\n"
        "Role:"
    )

    try:
        raw = _call_llm(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024, temperature=0.0, role="router",
        )
    except Exception as e:
        print(f"[Router] route_generation_model failed: {e} — using fallback '{fallback_role}'")
        return fallback_role

    raw_lower = raw.lower()
    multi_pos = raw_lower.rfind("multi")
    rag_pos   = raw_lower.rfind("rag")
    kimi_pos  = raw_lower.rfind("kimi")
    llama_pos = raw_lower.rfind("llama")

    if multi_pos == -1 and rag_pos == -1 and kimi_pos == -1 and llama_pos == -1:
        print(f"[Router] No role found — using fallback '{fallback_role}'")
        return fallback_role

    if kimi_pos != -1 or llama_pos != -1:
        return "multi" if max(kimi_pos, -1) > max(llama_pos, -1) else "rag"

    return "multi" if multi_pos > rag_pos else "rag"
