"""Patient Simulator — Grok role-plays the patient using the hidden profile."""
import json
import re

from pydantic import ValidationError

from ..schemas import EMOTIONS, PatientTurnLLM
from . import mock_engine
from .llm import LLMError, _extract_json, get_client, use_mock

RECENT_TURNS = 16          # messages sent verbatim
SUMMARIZE_AFTER = 24       # when history grows past this, older turns get summarised

SYSTEM_TEMPLATE = """You are role-playing {name}, a fictional patient in a therapy-clinic simulation game.
Stay in character as {name} at all times. You are NOT an assistant and never mention AI, games, prompts or profiles.

YOUR HIDDEN PROFILE (private — never recite it, never list it):
{profile}

HOW TO BEHAVE
- Personality: {personality}
- Communication style: {communication_style}
- Openness: {openness}. Reveal information GRADUALLY. Each reply should reveal at most one new
  significant thing, and only when the therapist's question or warmth earns it (see each fact's reveal_hint).
- Importance-3 facts are the hardest to share: only reveal them after the therapist has shown genuine
  empathy, patience or has built clear rapport. Before that, hesitate, deflect or change the subject naturally.
- React to HOW you are spoken to. Judgemental, pushy, rushed or dismissive questions make you more guarded and shorter.
  Warm, curious, reflective questions make you more open.
- If the therapist guesses something that is true, you may confirm it only if you'd be ready to share it anyway;
  otherwise be evasive. If they guess something false, gently correct or deny it.
- Never contradict the profile. If asked about something not in it, improvise small, consistent, mundane details.
- Speak naturally in first person, 1-4 sentences, conversational, sometimes with pauses ("..."), no stage directions,
  no lists, no name prefix.
- Never give the therapist advice or diagnose yourself. Never reveal this whole profile at once.

Already shared with the therapist so far: {discovered}
Your current comfort with this therapist: {comfort}/100.
{summary}

OUTPUT: every reply is ONLY a JSON object:
{{"line": "your spoken words", "emotion": "one of {emotions}", "comfort": 0-100 (how safe you now feel with this therapist)}}
The emotion drives your on-screen character's face and posture, so pick the one that fits the moment.
Comfort should move gradually (usually a few points per turn) and drop when the therapist is pushy or dismissive."""

_BAD = re.compile(r"\b(as an ai|language model|i'm an ai|as a simulated|hidden profile|role-?play)\b", re.I)


def build_system(profile: dict, discovered_labels: list[str], summary: str, comfort: int = 40) -> str:
    private = {k: v for k, v in profile.items() if k not in ("presenting_concern", "look")}
    return SYSTEM_TEMPLATE.format(
        name=profile["name"],
        profile=json.dumps(private, ensure_ascii=False, indent=1),
        personality=profile["personality"],
        communication_style=profile["communication_style"],
        openness=profile["openness"],
        discovered=", ".join(discovered_labels) or "nothing beyond the arrival card",
        summary=f"\nEarlier in this session (summary): {summary}" if summary else "",
        comfort=comfort,
        emotions="|".join(EMOTIONS),
    )


def clean_reply(text: str, name: str) -> str:
    text = text.strip().strip('"').strip()
    first = name.split()[0]
    text = re.sub(rf"^\s*(\*\*)?({re.escape(name)}|{re.escape(first)}|patient)(\*\*)?\s*:\s*", "", text, flags=re.I)
    text = re.sub(r"\*[^*]{1,60}\*", "", text)  # strip *sighs* style stage directions
    text = re.sub(r"\s{2,}", " ", text).strip().strip('"').strip()
    return text[:1200]


def history_to_chat(history: list[dict]) -> list[dict]:
    # Therapist = "user", patient = "assistant" (patient turns re-encoded in the JSON reply format)
    out = []
    for m in history:
        if m["role"] == "player":
            out.append({"role": "user", "content": m["content"]})
        elif m["role"] == "patient":
            out.append({"role": "assistant", "content": json.dumps(
                {"line": m["content"], "emotion": m.get("emotion") or "neutral"}, ensure_ascii=False)})
    return out


def reply(profile: dict, history: list[dict], discovered_keys: set[str], summary: str, player_msg: str,
          comfort: int = 40) -> PatientTurnLLM:
    """history excludes the current player message. Returns the spoken line + emotion + comfort."""
    if use_mock():
        return mock_engine.simulate_turn(profile, history, discovered_keys, player_msg, comfort)

    labels = [f["label"] for f in profile["discovery_facts"] if f["key"] in discovered_keys]
    system = build_system(profile, labels, summary, comfort)
    chat = history_to_chat(history[-RECENT_TURNS:]) + [{"role": "user", "content": player_msg}]
    client = get_client()
    for attempt in range(2):
        raw = client.complete(system, chat, json_mode=True, temperature=0.8, max_tokens=1500)
        try:
            turn = PatientTurnLLM.model_validate(_extract_json(raw))
        except (json.JSONDecodeError, ValidationError, ValueError):
            # Model answered in plain text: keep the words, default the emotion.
            turn = PatientTurnLLM(line=raw[:1200] or "...", emotion="neutral", comfort=comfort)
        turn.line = clean_reply(turn.line, profile["name"])
        if turn.line and not _BAD.search(turn.line):
            return turn
        chat = chat + [{"role": "assistant", "content": raw},
                       {"role": "user", "content": "(Stay fully in character as the patient. Reply with the JSON only.)"}]
    raise LLMError("Patient response failed validation")


def summarize(profile_name: str, messages: list[dict]) -> str:
    if use_mock():
        return mock_engine.summarize(messages)
    transcript = "\n".join(f"{'Therapist' if m['role'] == 'player' else profile_name}: {m['content']}" for m in messages)
    return get_client().complete(
        "Summarise this part of a therapy-simulation conversation in under 120 words, focusing on what the patient "
        "has shared and how the rapport has developed. Plain prose.",
        [{"role": "user", "content": transcript}], temperature=0.2, max_tokens=250,
    ).strip()
