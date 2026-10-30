"""Grok (xAI) client. xAI exposes an OpenAI-compatible Chat Completions API:
POST {GROK_BASE_URL}/chat/completions  with  Authorization: Bearer {GROK_API_KEY}.
"""
import json
import logging
import re
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from ..config import get_settings

log = logging.getLogger("llm")
T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


class _FatalLLMError(LLMError):
    pass


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


class GrokClient:
    def __init__(self) -> None:
        s = get_settings()
        if not s.grok_api_key:
            raise LLMError("GROK_API_KEY is not configured")
        self.url = s.grok_base_url.rstrip("/") + "/chat/completions"
        self.model = s.grok_model
        self.headers = {"Authorization": f"Bearer {s.grok_api_key}", "Content-Type": "application/json"}
        self.timeout = s.grok_timeout_seconds

    def complete(
        self,
        system: str,
        messages: list[dict],
        *,
        json_mode: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 1200,
    ) -> str:
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, *messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        last_err: Exception | None = None
        adapted: set[str] = set()
        attempt = 0
        while attempt < 3:
            try:
                r = httpx.post(self.url, headers=self.headers, json=body, timeout=self.timeout)
                if r.status_code in (429, 500, 502, 503, 504):
                    raise LLMError(f"Grok API {r.status_code}: {r.text[:300]}")
                if r.status_code == 400:
                    # Some models reject optional parameters. Drop the offending one and retry once.
                    fixed = self._adapt_body(body, r.text, adapted)
                    if fixed:
                        log.warning("Grok rejected '%s' for model %s; retrying without it", fixed, self.model)
                        continue
                if r.status_code >= 400:
                    log.error("Grok API %s for model %r: %s", r.status_code, self.model, r.text[:1000])
                    raise _FatalLLMError(f"Grok API {r.status_code}: {r.text[:500]}")
                choice = r.json()["choices"][0]
                content = choice["message"].get("content") or ""
                if not content.strip():
                    raise LLMError(f"Empty completion (finish_reason={choice.get('finish_reason')})")
                return content
            except _FatalLLMError as e:
                last_err = e
                break
            except (httpx.HTTPError, LLMError, KeyError, ValueError) as e:
                last_err = e
                log.warning("Grok call failed (attempt %s): %s", attempt + 1, e)
                time.sleep(0.8 * (attempt + 1))
            attempt += 1
        raise LLMError(str(last_err))

    @staticmethod
    def _adapt_body(body: dict, error_text: str, adapted: set[str]) -> str | None:
        err = error_text.lower()
        for key in ("response_format", "temperature", "max_tokens"):
            if key in err and key in body and key not in adapted:
                adapted.add(key)
                value = body.pop(key)
                if key == "max_tokens":
                    body["max_completion_tokens"] = value
                return key
        return None

    def complete_json(self, system: str, user: str, model_cls: type[T], *, temperature: float = 0.4,
                      max_tokens: int = 3000) -> T:
        messages = [{"role": "user", "content": user}]
        for attempt in range(2):
            raw = self.complete(system, messages, json_mode=True, temperature=temperature, max_tokens=max_tokens)
            try:
                return model_cls.model_validate(_extract_json(raw))
            except (json.JSONDecodeError, ValidationError) as e:
                log.warning("JSON validation failed (attempt %s): %s", attempt + 1, e)
                messages = messages + [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": f"That JSON was invalid: {str(e)[:800]}\nReturn ONLY corrected JSON."},
                ]
        raise LLMError(f"Could not get valid {model_cls.__name__} JSON from Grok")


_client: GrokClient | None = None


def get_client() -> GrokClient:
    global _client
    if _client is None:
        _client = GrokClient()
    return _client


def use_mock() -> bool:
    return get_settings().effective_llm_mode == "mock"
