import re
from app.shared.utils import cosine_similarity

CONVERSATIONAL_PATTERNS = [

    r"^(hi|hey|hello|howdy|hiya|sup|what'?s up|yo)\b",
    r"^good (morning|afternoon|evening|night|day)\b",
    r"^(namaste|salaam|namaskar)\b",

    r"^(bye|goodbye|see you|see ya|later|cya|ttyl|take care)\b",
    r"^(good night|good bye)\b",

    r"^(thanks|thank you|thank u|thx|ty|cheers|appreciated)\b",
    r"^(great|awesome|perfect|wonderful|excellent|fantastic)\s*[!.]?$",
    r"^(ok|okay|got it|understood|makes sense|cool|nice)\s*[!.]?$",

    r"^how are you\b",
    r"^how'?s it going\b",
    r"^what'?s (up|new|going on)\b",
    r"^(are you (okay|alright|good|fine|there|ready))\b",

    r"^what (can|do) you do\b",
    r"^(who|what) are you\b",
    r"^(tell me about yourself|introduce yourself)\b",
    r"^(help|can you help( me)?)\s*[?!.]?$",

    r"^(yes|no|yeah|nope|yep|nah|sure|of course|absolutely)\s*[!.]?$",
]

_COMPILED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in CONVERSATIONAL_PATTERNS
]

_DOCUMENT_SIGNALS = [
    "my document", "my pdf", "my file", "my notes",
    "my paper", "uploaded", "the document", "the pdf",
    "the file", "the paper", "the notes", "the text",
    "in the document", "in my", "from my", "from the",
    "page ", "pages ", "chapter ", "section ",
    "summarise", "summarize", "summarised", "summarized",
    "according to", "what does it say", "what does the",
    "doc ", "document ",
]

_CONVERSATIONAL_PATTERNS_BY_KEY: dict[str, list[str]] = {
    "greeting": ["hi", "hey", "hello", "howdy", "hiya", "sup", "yo",
                 "good morning", "good afternoon", "good evening",
                 "good night", "good day", "namaste", "salaam", "namaskar"],
    "farewell": ["bye", "goodbye", "see you", "see ya", "later", "cya",
                 "ttyl", "take care"],
    "thanks": ["thank", "thanks", "thx", "ty", "cheers", "appreciated"],
    "how_are_you": ["how are you", "how's it", "how are u"],
    "what_can_you_do": ["what can you do", "what do you do",
                        "who are you", "what are you",
                        "tell me about yourself", "introduce yourself"],
    "acknowledgement": ["yes", "no", "yeah", "nope", "yep", "ok",
                        "okay", "got it", "understood", "cool",
                        "great", "awesome", "perfect", "nice"],
}

CONVERSATIONAL_RESPONSES = {
    "greeting": (
        "Hello! I'm your document assistant. "
        "You can upload PDFs and ask me questions about them. "
        "What would you like to know?"
    ),
    "farewell": (
        "Goodbye! Feel free to come back anytime "
        "if you have more questions about your documents."
    ),
    "thanks": (
        "You're welcome! Is there anything else "
        "you'd like to know from your documents?"
    ),
    "how_are_you": (
        "I'm doing well, thanks for asking! "
        "I'm ready to help you explore your documents. "
        "What would you like to know?"
    ),
    "what_can_you_do": (
        "I can help you find information in your uploaded documents. "
        "Upload a PDF and ask me anything about it — "
        "I'll search through it and give you precise answers. "
        "I also remember our conversation so you can ask follow-up questions."
    ),
    "acknowledgement": (
        "Got it! Let me know if you have any questions "
        "about your documents."
    ),
    "default": (
        "Hello! I'm here to help you with your documents. "
        "What would you like to know?"
    ),
}


def classify_query(
    query:           str,
    query_embedding: list[float] | None = None,
) -> dict:
    cleaned = query.strip()

    layer1_result = _classify_by_rules(cleaned)

    if layer1_result is not None:
        print(f"[Classifier] Layer 1 match: "
              f"'{cleaned[:60]}' → conversational ({layer1_result})")
        return {
            "type":     "conversational",
            "response": CONVERSATIONAL_RESPONSES.get(
                layer1_result,
                CONVERSATIONAL_RESPONSES["default"]
            ),
        }

    if query_embedding is not None:
        layer2_result = _classify_by_embedding(cleaned, query_embedding)
        print(f"[Classifier] Layer 2: "
              f"'{cleaned[:60]}' → {layer2_result}")
        return {"type": layer2_result}

    print(f"[Classifier] No embedding available — "
          f"defaulting to document query")
    return {"type": "document"}


def get_conversational_response(query: str) -> str | None:
    cleaned      = query.strip()
    layer1_result = _classify_by_rules(cleaned)

    if layer1_result is not None:
        return CONVERSATIONAL_RESPONSES.get(
            layer1_result,
            CONVERSATIONAL_RESPONSES["default"]
        )

    return None


def _has_document_signal(query_lower: str) -> bool:
    return any(signal in query_lower for signal in _DOCUMENT_SIGNALS)


def _classify_by_rules(query: str) -> str | None:
    q_lower = query.lower().strip()

    if _has_document_signal(q_lower):
        return None

    for pattern in _COMPILED_PATTERNS:
        if pattern.match(q_lower):
            return _get_response_key(q_lower)

    words = q_lower.split()
    if len(words) <= 2 and "?" not in query and not _looks_like_question(q_lower):
        if not _has_document_signal(q_lower):
            return "default"

    return None


def _get_response_key(query: str) -> str:
    q = query.lower()

    if any(word in q for word in
           ["bye", "goodbye", "see you", "later", "take care", "night"]):
        return "farewell"

    if any(word in q for word in
           ["thank", "thanks", "thx", "ty", "cheers", "appreciated"]):
        return "thanks"

    if any(phrase in q for phrase in
           ["how are you", "how's it", "how are u"]):
        return "how_are_you"

    if any(phrase in q for phrase in
           ["what can you do", "what do you do",
            "who are you", "what are you",
            "tell me about yourself", "introduce yourself"]):
        return "what_can_you_do"

    if any(word in q for word in
           ["yes", "no", "yeah", "nope", "yep", "ok",
            "okay", "got it", "understood", "cool",
            "great", "awesome", "perfect", "nice"]):
        return "acknowledgement"

    return "greeting"


def _classify_by_embedding(
    query:           str,
    query_embedding: list[float],
) -> str:
    q_lower = query.lower()

    document_signals = [
        "my document", "my pdf", "my file", "my notes",
        "my paper", "uploaded", "the document", "the pdf",
        "the file", "the paper", "the notes", "the text",
        "page ", "chapter ", "section ",
        "summarise", "summarize", "according to",
        "what does it say", "what does the",
        "in the document", "in my", "from my",
        "based on", "from the",
    ]

    if any(signal in q_lower for signal in document_signals):
        return "document"

    general_signals = [
        "what is the capital",
        "who invented",
        "when was",
        "how many",
        "what year",
        "who is the president",
        "what does the word",
        "define ",
        "meaning of ",
        "translate ",
        "what time",
        "what's the weather",
        "calculate ",
        "how many days",
    ]

    if any(signal in q_lower for signal in general_signals):
        return "general"

    return "document"


def _looks_like_question(query: str) -> bool:
    question_starters = [
        "what", "where", "when", "why", "who",
        "how", "which", "can", "could", "would",
        "should", "is", "are", "does", "do", "did",
    ]

    first_word = query.split()[0] if query.split() else ""
    return first_word in question_starters or "?" in query
