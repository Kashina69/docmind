import re

_PAGE_RE = re.compile(
    r'\b(?:page|pg)\.?\s*(?:number\s*|#\s*)?(\d+)\b',
    re.IGNORECASE,
)

_SECTION_RE = re.compile(
    r'\b(?:section|chapter|part|unit|module|topic)\s+(["\']?[\w\s\-\.]{2,60}["\']?)',
    re.IGNORECASE,
)


def detect_structured_query(query: str) -> dict | None:
    page_m = _PAGE_RE.search(query)
    if page_m:
        return {"type": "page", "value": int(page_m.group(1))}

    section_m = _SECTION_RE.search(query)
    if section_m:
        raw = section_m.group(1).strip().strip("'\"")
        if raw:
            return {"type": "section", "value": raw}

    return None
