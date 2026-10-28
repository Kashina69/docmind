import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.pipelines.ingestion.structure_detector import detect_sections, Section

_PROSE_SPLITTER_ARGS = dict(
    separators   = ["\n\n", "\n", ". ", " ", ""],
    length_function = len,
    add_start_index = True,
)

_CODE_SPLITTER_ARGS = dict(
    separators   = ["\nclass ", "\ndef ", "\n\n", "\n", " ", ""],
    length_function = len,
    add_start_index = True,
)

_SENTENCE_END = re.compile(r'(?<=[.!?])\s+')


def chunk_pages(
    pages:              list[dict],
    chunk_size:         int = 600,
    chunk_overlap:      int = 150,
    global_chunk_offset: int = 0,
) -> list[dict]:
    sections = detect_sections(pages)

    if not sections:
        raise ValueError("Structure detector produced no sections — text may be empty.")

    prose_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap,
        **_PROSE_SPLITTER_ARGS,
    )
    code_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=0,
        **_CODE_SPLITTER_ARGS,
    )

    all_chunks:    list[dict] = []
    chunk_index:   int        = global_chunk_offset
    last_sentence: str | None = None

    for sec in sections:
        splitter = code_splitter if sec.content_type == "code" else prose_splitter
        docs     = splitter.create_documents([sec.text])

        for doc_idx, doc in enumerate(docs):
            raw_text = doc.page_content.strip()
            if not raw_text:
                continue

            first_word = raw_text.lstrip()[0] if raw_text.lstrip() else ""
            if (
                doc_idx == 0
                and last_sentence
                and first_word.islower()
                and sec.content_type == "prose"
            ):
                raw_text = f"{last_sentence} {raw_text}"

            prefix_parts = [f"[Page {sec.page_number}]"]
            if sec.heading:
                prefix_parts.append(f"[Section: {sec.heading}]")
            prefix   = " ".join(prefix_parts)
            content  = f"{prefix}\n{raw_text}"

            all_chunks.append({
                "content": content,
                "metadata": {
                    "page_number":     sec.page_number,
                    "page_number_end": sec.page_number,
                    "pages":           [sec.page_number],
                    "heading":         sec.heading,
                    "section_id":      sec.section_id,
                    "content_type":    sec.content_type,
                    "chunk_index":     chunk_index,
                    "char_count":      len(content),
                },
            })
            chunk_index += 1

            sentences = _SENTENCE_END.split(raw_text)
            last_sentence = sentences[-1].strip() if sentences else None

    if not all_chunks:
        raise ValueError("Chunking produced zero chunks.")

    cross_section = 0
    print(
        f"[Chunker] {len(all_chunks)} chunks, "
        f"chunk_size={chunk_size}, overlap={chunk_overlap}, "
        f"sections={len(sections)}"
    )
    return all_chunks
