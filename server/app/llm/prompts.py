import re

STYLE_INSTRUCTIONS = {
    "concise": (
        "Write a short answer in 3-5 lines.\n"
        "No bullets, no sections, no extra explanation.\n"
        "Only include the most important information."
    ),
    "explanatory": (
        "You MUST follow this exact structure:\n"
        "Answer:<1-2 line direct answer>\n"
        "Explanation:\n"
        "- What it is: <1-2 lines>\n"
        "- How it works: <2-3 lines>\n"
        "- Why it matters: <1-2 lines>\n"
        "Rules:\n"
        "- Always include all three sections\n"
        "- Keep explanations concise but clear\n"
        "- Do not skip sections\n"
        "- Do not write long paragraphs"
    ),
    "conversational": (
        "Explain like you're talking to a friend.\n"
        "- Use simple language\n"
        "- Use analogies if helpful\n"
        "- Avoid structured sections\n"
        "- Keep it natural and easy to follow"
    ),
}


def strip_think_tags(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def format_history(history: list[dict]) -> str:
    if not history:
        return ""
    lines = ["\nPrior conversation:"]
    for msg in history:
        label = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{label}: {msg['content']}")
    return "\n".join(lines) + "\n"


def build_rag_prompt(
    query:          str,
    context_chunks: list[dict],
    history:        list[dict],
    style:          str = "explanatory",
) -> str:
    by_doc: dict[str, list] = {}
    for chunk in context_chunks:
        fname = chunk["metadata"].get("filename", "document")
        by_doc.setdefault(fname, []).append(chunk)

    context_lines = []
    chunk_num = 1
    for fname, chunks in by_doc.items():
        context_lines.append(f"=== Document: {fname} ===")
        for chunk in chunks:
            section      = chunk["metadata"].get("section", "")
            section_part = f" | Section: {section}" if section else ""
            context_lines.append(
                f"[Chunk {chunk_num} - Page {chunk['metadata'].get('page_number', '?')}"
                f"{section_part}]\n{chunk['content']}"
            )
            chunk_num += 1

    context_block = "\n\n".join(context_lines)
    history_text  = format_history(history)
    style_block   = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["explanatory"])

    multi_doc_note = (
        "\nImportant: chunks come from multiple documents. "
        "Synthesize across all of them into a single coherent answer. "
        "Reference document names only if the distinction matters.\n"
        if len(by_doc) > 1 else ""
    )

    return f"""You are a knowledgeable tutor helping a student understand their uploaded documents.

{style_block}
{multi_doc_note}
Context usage:
- Use retrieved chunks as the primary source
- Combine multiple chunks into one coherent explanation
- Simplify fragmented context

Rules:
- Do NOT say "based on the context"
- If not found in documents: "This is not clearly covered in your document. Based on my knowledge: [answer]"
- Never fabricate document content
{history_text}
Document context:
{context_block}

Current question: {query}

Answer:"""


def build_direct_prompt(query: str, history: list[dict], style: str) -> str:
    history_text = format_history(history)
    style_block  = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["explanatory"])

    return f"""You are a helpful assistant. Answer the following question accurately using your own knowledge.

{style_block}
{history_text}
Question: {query}

Answer:"""
