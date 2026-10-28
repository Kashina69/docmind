import re
from dataclasses import dataclass, field


@dataclass
class Section:
    heading:      str | None
    content_type: str
    text:         str
    page_number:  int
    section_id:   str


_HEADING_PATTERNS = [
    re.compile(r'^(\d+\.)+\d*\s+\S', re.MULTILINE),
    re.compile(r'^[A-Z]{1,5}\.\s+\S', re.MULTILINE),
    re.compile(r'^#{1,4}\s+\S', re.MULTILINE),
    re.compile(r'^[A-Z][A-Z\s\-]{3,60}$', re.MULTILINE),
    re.compile(r'^(Chapter|Section|Part|Unit|Module|Lecture)\s+[\dIVXA-Z]', re.MULTILINE | re.IGNORECASE),
]

_CODE_KEYWORDS = re.compile(
    r'^\s*(def |class |function |public |private |void |int |float |bool |'
    r'return |import |from |#include |SELECT |INSERT |UPDATE |DELETE |'
    r'if\s*\(|for\s*\(|while\s*\(|switch\s*\()',
    re.MULTILINE,
)
_LEADING_SPACES = re.compile(r'^( {4}|\t)', re.MULTILINE)
_FENCE          = re.compile(r'^```', re.MULTILINE)

_LIST_LINE      = re.compile(r'^(\s*)([-*•]|\d+[.)]\s|[a-zA-Z][.)]\s)\S', re.MULTILINE)

_TABLE_LINE     = re.compile(r'^.*(\|.*){2,}', re.MULTILINE)
_TABLE_TAB      = re.compile(r'^[^\n]*\t[^\n]*\t[^\n]*', re.MULTILINE)


def detect_sections(pages: list[dict]) -> list[Section]:
    all_sections: list[Section] = []
    current_heading: str | None  = None

    for page in pages:
        page_number = page["page_number"]
        page_text   = page["text"]

        sections = _split_page_into_sections(page_text, page_number)

        for sec in sections:
            if sec.content_type == "heading":
                current_heading = sec.heading
                continue

            sec.heading = current_heading
            all_sections.append(sec)

    return all_sections


def _split_page_into_sections(text: str, page_number: int) -> list[Section]:
    lines    = text.splitlines(keepends=True)
    sections: list[Section] = []
    buffer:  list[str]      = []
    cur_type: str           = "prose"
    sec_idx:  int           = 0
    in_fence: bool          = False

    def _flush(t: str) -> None:
        nonlocal sec_idx
        raw = "".join(buffer).strip()
        if not raw:
            return
        heading = raw if t == "heading" else None
        sections.append(Section(
            heading=heading,
            content_type=t,
            text=raw,
            page_number=page_number,
            section_id=f"p{page_number}s{sec_idx}",
        ))
        sec_idx += 1
        buffer.clear()

    for line in lines:
        stripped = line.rstrip()

        if _FENCE.match(stripped):
            if not in_fence:
                _flush(cur_type)
                cur_type = "code"
                in_fence = True
            else:
                in_fence = False
                _flush("code")
                cur_type = "prose"
            continue

        if in_fence:
            buffer.append(line)
            continue

        line_type = _classify_line(stripped)

        if line_type != cur_type:
            if not stripped and len(buffer) > 0:
                buffer.append(line)
                continue
            _flush(cur_type)
            cur_type = line_type

        buffer.append(line)

    _flush(cur_type)
    return sections


def _classify_line(line: str) -> str:
    if not line.strip():
        return "prose"

    if len(line.strip()) < 120:
        for pat in _HEADING_PATTERNS:
            if pat.match(line.strip()):
                return "heading"

    if _TABLE_LINE.match(line) or _TABLE_TAB.match(line):
        return "table"

    if _LEADING_SPACES.match(line) or _CODE_KEYWORDS.match(line):
        return "code"

    if _LIST_LINE.match(line):
        return "list"

    return "prose"
