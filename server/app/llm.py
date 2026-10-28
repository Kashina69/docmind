import os
import re
import time

import requests
from app.secrets import get_secret

MAX_RETRIES = 3
RETRY_DELAY = 2

_CFG_DEFAULTS = {
    "rag_model":       "llama-3.3-70b-versatile",
    "multi_model":     "moonshotai/kimi-k2.6",
    "summarizer_model": "nvidia/llama-3.3-nemotron-super-49b-v1.5",
    "hyde_model":      None,
    "router_model":    None,
    "rewrite_model":   None,
}


def _api_url() -> str:
    return (os.getenv("LLM_API_URL") or get_secret("LLM_API_URL")).rstrip("/")


def _api_key() -> str:
    return os.getenv("LLM_API_KEY") or get_secret("LLM_API_KEY")


def _model(role: str) -> str:
    env_key = f"MODEL_{role.upper()}"
    if os.getenv(env_key):
        return os.getenv(env_key).strip()
    try:
        val = get_secret(env_key)
        if val:
            return val.strip()
    except Exception:
        pass
    mapped = {
        "rag":        _CFG_DEFAULTS["rag_model"],
        "multi":      _CFG_DEFAULTS["multi_model"],
        "hyde":       _CFG_DEFAULTS["hyde_model"] or _CFG_DEFAULTS["rag_model"],
        "router":     _CFG_DEFAULTS["router_model"] or _CFG_DEFAULTS["rag_model"],
        "rewrite":    _CFG_DEFAULTS["rewrite_model"] or _CFG_DEFAULTS["rag_model"],
        "summarizer": _CFG_DEFAULTS["summarizer_model"],
    }
    return mapped[role] or _CFG_DEFAULTS["rag_model"]


_THINKING_ALIASES = {
    "minimal": "low",
    "min": "low",
    "xhigh": "max",
    "ultra": "max",
}

_THINKING_LEVELS = ("low", "medium", "high", "max")


def _thinking_raw(role: str) -> str:
    for key in (f"THINKING_{role.upper()}", "THINKING_DEFAULT", "THINKING_LEVEL"):
        val = os.getenv(key)
        if val and val.strip():
            return val.strip()
        try:
            val = get_secret(key)
            if val and val.strip():
                return val.strip()
        except Exception:
            pass
    return ""


def _thinking_params(role: str, api_url: str) -> dict:
    raw = _thinking_raw(role).strip().lower()
    if not raw:
        return {}

    is_deepseek = "deepseek" in (api_url or "").lower()

    if raw in ("disabled", "off", "none", "false", "no", "0"):
        if is_deepseek:
            return {"thinking": {"type": "disabled"}}
        return {}

    effort = _THINKING_ALIASES.get(raw, raw)
    if effort not in _THINKING_LEVELS:
        print(f"[LLM:{role}] Ignoring unknown thinking level '{raw}' "
              f"(use disabled/low/medium/high/max)")
        return {}

    params: dict = {}
    if is_deepseek:
        params["reasoning_effort"] = effort
        params["thinking"] = {"type": "enabled"}
    else:
        params["reasoning_effort"] = "high" if effort == "max" else effort
    return params


def _extract_content(data: dict) -> str:
    try:
        msg = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        return ""
    content = msg.get("content") or ""
    if content.strip():
        return content
    return msg.get("reasoning_content") or ""


def _call_llm(
    messages:    list[dict],
    max_tokens:  int,
    temperature: float,
    role:        str = "rag",
    model:       str | None = None,
    top_p:       float | None = None,
    extra:       dict | None = None,
) -> str:
    url         = f"{_api_url()}/chat/completions"
    api_key     = _api_key()
    model_id    = model or _model(role)
    retry_delay = RETRY_DELAY

    if not api_key or not url.startswith("http"):
        raise ValueError(f"[LLM] LLM_API_URL / LLM_API_KEY missing — set them in .env")

    body: dict = {
        "model":       model_id,
        "messages":    messages,
        "max_tokens":  max_tokens,
        "temperature": temperature,
        "stream":      False,
    }
    body.update(_thinking_params(role, url))
    if top_p is not None:
        body["top_p"] = top_p
    if extra:
        body.update(extra)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type":  "application/json",
                    "Accept":        "application/json",
                },
                json=body,
                timeout=90,
            )

            if response.status_code == 200:
                return _extract_content(response.json())

            elif response.status_code == 429:
                wait = retry_delay * attempt * 2
                print(f"[LLM:{role}/{model_id}] Rate limited. Waiting {wait}s (attempt {attempt}/{MAX_RETRIES})")
                time.sleep(wait)

            elif response.status_code >= 500:
                print(f"[LLM:{role}/{model_id}] Server error {response.status_code}. Waiting {retry_delay}s (attempt {attempt}/{MAX_RETRIES})")
                time.sleep(retry_delay)
                retry_delay *= 2

            else:
                raise ValueError(f"[LLM:{role}/{model_id}] API error {response.status_code}: {response.text}")

        except requests.exceptions.Timeout:
            print(f"[LLM:{role}/{model_id}] Timeout. Waiting {retry_delay}s (attempt {attempt}/{MAX_RETRIES})")
            time.sleep(retry_delay)
            retry_delay *= 2

        except requests.exceptions.ConnectionError:
            print(f"[LLM:{role}/{model_id}] Connection error. Waiting {retry_delay}s (attempt {attempt}/{MAX_RETRIES})")
            time.sleep(retry_delay)
            retry_delay *= 2

    raise Exception(f"[LLM:{role}/{model_id}] API failed after {MAX_RETRIES} attempts. Job will be retried.")


def generate(messages: list[dict], max_tokens: int = 4096, temperature: float = 0.6) -> str:
    return _call_llm(messages=messages, max_tokens=max_tokens, temperature=temperature, role="summarizer")


def generate_json(messages: list[dict], max_tokens: int = 2048, temperature: float = 0.3) -> list[dict]:
    import json

    raw = generate(messages, max_tokens=max_tokens, temperature=temperature)

    stripped = raw.strip()
    if stripped.startswith("["):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass

    match = re.search(r"\[.*?\]", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"[LLM:summarizer] generate_json: could not parse JSON array from response. "
        f"Raw (first 200 chars): {raw[:200]}"
    )
