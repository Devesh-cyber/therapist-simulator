"""Grok client tests with the HTTP layer stubbed (no network, no key needed)."""
import json

import httpx
import pytest

from app.config import get_settings
from app.schemas import DiscoveryResultLLM
from app.services import llm


class Resp:
    def __init__(self, code, content):
        self.status_code, self._c, self.text = code, content, str(content)

    def json(self):
        return {"choices": [{"message": {"content": self._c}}]}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(get_settings(), "grok_api_key", "test-key")
    monkeypatch.setattr(llm.time, "sleep", lambda *_: None)
    return llm.GrokClient()


def test_request_shape_and_json_retry(client, monkeypatch):
    calls = []
    replies = iter(["not json at all", '```json\n{"discoveries":[{"key":"a","confidence":0.9,"evidence":"x"}]}\n```'])

    def fake_post(url, headers, json, timeout):
        calls.append((url, headers, json))
        return Resp(200, next(replies))

    monkeypatch.setattr(httpx, "post", fake_post)
    out = client.complete_json("sys", "user", DiscoveryResultLLM)
    assert out.discoveries[0].key == "a"
    url, headers, body = calls[0]
    assert url.endswith("/chat/completions") and headers["Authorization"] == "Bearer test-key"
    assert body["messages"][0] == {"role": "system", "content": "sys"}
    assert body["response_format"] == {"type": "json_object"}
    assert len(calls) == 2  # retried after invalid JSON


def test_retries_transient_then_fails_fast_on_4xx(client, monkeypatch):
    seq = iter([Resp(503, "busy"), Resp(200, "hello")])
    monkeypatch.setattr(httpx, "post", lambda *a, **k: next(seq))
    assert client.complete("s", [{"role": "user", "content": "hi"}]) == "hello"

    n = {"c": 0}

    def bad(*a, **k):
        n["c"] += 1
        return Resp(401, "bad key")

    monkeypatch.setattr(httpx, "post", bad)
    with pytest.raises(llm.LLMError):
        client.complete("s", [{"role": "user", "content": "hi"}])
    assert n["c"] == 1


def test_patient_reply_cleanup():
    from app.services.patient_simulator import clean_reply
    assert clean_reply('Rahul: *sighs* "I guess so."', "Rahul Mehta") == "I guess so."


def test_patient_turn_json_and_plaintext_fallback(client, monkeypatch):
    from app.services import patient_simulator
    monkeypatch.setattr(patient_simulator, "use_mock", lambda: False)
    monkeypatch.setattr(patient_simulator, "get_client", lambda: client)
    profile = {"name": "Rahul Mehta", "personality": "p", "communication_style": "c", "openness": "medium",
               "discovery_facts": [], "look": {"gender": "man"}}
    replies = iter(['{"line": "Rahul: I guess work is a lot.", "emotion": "ANXIOUS", "comfort": 47}',
                    "Honestly I just feel tired."])
    monkeypatch.setattr(httpx, "post", lambda *a, **k: Resp(200, next(replies)))
    t = patient_simulator.reply(profile, [], set(), "", "How are you?", 40)
    assert (t.line, t.emotion, t.comfort) == ("I guess work is a lot.", "anxious", 47)
    t2 = patient_simulator.reply(profile, [{"role": "patient", "content": "hi", "emotion": "sad"}], set(), "", "Go on", 40)
    assert t2.line == "Honestly I just feel tired." and t2.emotion == "neutral"


def test_400_drops_rejected_param_and_retries(client, monkeypatch):
    bodies = []

    def fake(url, headers, json, timeout):
        bodies.append(dict(json))
        if "response_format" in json:
            return Resp(400, "Argument not supported on this model: response_format")
        return Resp(200, '{"discoveries": []}')

    monkeypatch.setattr(httpx, "post", fake)
    out = client.complete_json("s", "u", DiscoveryResultLLM)
    assert out.discoveries == [] and len(bodies) == 2 and "response_format" not in bodies[1]
