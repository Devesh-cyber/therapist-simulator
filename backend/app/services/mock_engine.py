"""Offline demo engine used when GROK_API_KEY is not set (LLM_MODE=mock or auto without key).

It lets you click through the whole game and run the test-suite without an API key.
It is intentionally simple (keyword based) — the real semantic behaviour comes from Grok.
The UI shows an "Offline demo AI" badge whenever this engine is active.
"""
import random
import re

from ..schemas import (
    CategoryScores, PatientProfileLLM, PatientTurnLLM, SatisfactionBreakdown, SessionEvaluationLLM, UnderstandingLLM,
)

STOP = set("the a an and or but to of in on at for with is are was were be been i you me my your it that this "
           "do does did have has had what how why when where who can could would should about tell feel "
           "feeling just so if any there their them they he she his her we our us not no yes".split())

EMPATHY = ["sounds", "understand", "must be", "that's hard", "thats hard", "difficult", "thank you for sharing",
           "i hear", "makes sense", "take your time", "it's okay", "its okay", "sorry", "valid", "brave", "appreciate"]
OPEN_Q = ["how", "what", "tell me", "can you describe", "could you share", "in what way", "walk me through"]


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z']+", text.lower()) if w not in STOP and len(w) > 2}


TEMPLATES = [
    {
        "name": "Rahul Mehta", "age": 24, "occupation": "Software Developer",
        "look": {"gender": "man", "skin": 3, "hair": "short", "hair_color": "black", "outfit": "#4F6D8F", "glasses": True, "beard": False},
        "presenting_concern": "I've been having trouble concentrating at work lately. I feel exhausted even after sleeping, and everything seems overwhelming.",
        "reported_symptoms": ["Difficulty concentrating", "Persistent tiredness", "Feeling overwhelmed"],
        "personality": "Polite, analytical, downplays his own feelings, uses humour to deflect.",
        "communication_style": "Short answers at first; opens up when he feels he isn't being judged.",
        "openness": "medium",
        "background": "Grew up in Pune, first in his family to work in tech. Moved to Bengaluru 14 months ago for his first job.",
        "emotional_concerns": ["Self-doubt", "Fear of disappointing family"],
        "underlying_concerns": ["Ties self-worth to work performance", "Isolation after relocating"],
        "life_events": ["Relocated to a new city for work", "Missed a promotion cycle three months ago"],
        "relationships": "Close to his mother, calls home weekly but hides his stress; few friends in the new city.",
        "session_objective": "Understand what is driving Rahul's exhaustion and overwhelm, and agree on supportive next steps.",
        "possible_next_steps": ["Explore workload and boundaries at work", "Build social connection in the new city",
                                "Work on self-compassion and unhelpful comparisons", "Regular follow-up sessions"],
        "discovery_facts": [
            {"key": "work_pressure", "category": "Symptoms and Experiences", "label": "Heavy workplace pressure", "importance": 2,
             "fact": "Deadlines have doubled since a reorganisation and he regularly works until midnight.",
             "patient_line": "Since the team reorg, my deadlines basically doubled. I'm online till midnight most days.",
             "related_keys": ["missed_promotion"], "reveal_hint": "Shares readily if asked about work or recent changes."},
            {"key": "comparison", "category": "Emotional State", "label": "Comparing himself to colleagues", "importance": 2,
             "fact": "Constantly compares himself to colleagues who seem faster and more confident.",
             "patient_line": "Everyone on my team seems so much quicker than me. I keep comparing myself to them.",
             "related_keys": ["self_doubt"], "reveal_hint": "When asked about colleagues or how he sees himself."},
            {"key": "self_doubt", "category": "Underlying Concerns", "label": "Deep self-doubt", "importance": 3,
             "fact": "Believes he is not good enough and might have been hired by mistake.",
             "patient_line": "Honestly... sometimes I think they hired me by mistake. Like I'm not actually good enough.",
             "related_keys": ["comparison", "family_expectations"], "reveal_hint": "Only after rapport and empathy."},
            {"key": "family_expectations", "category": "Relationships and Social Environment", "label": "Fear of disappointing family", "importance": 3,
             "fact": "Worries intensely about disappointing his parents, who sacrificed to fund his education.",
             "patient_line": "My parents sacrificed a lot for my degree. I can't let them down. I don't tell them how bad it is.",
             "related_keys": ["self_doubt"], "reveal_hint": "When asked about family or what's at stake."},
            {"key": "relocation", "category": "Important Life Events", "label": "Moved city for the job", "importance": 1,
             "fact": "Moved from Pune to Bengaluru 14 months ago for this job.",
             "patient_line": "I moved here from Pune about a year ago for this job.",
             "related_keys": ["isolation"], "reveal_hint": "When asked about background or recent changes."},
            {"key": "isolation", "category": "Relationships and Social Environment", "label": "Socially isolated", "importance": 2,
             "fact": "Has almost no friends in the new city and spends weekends alone.",
             "patient_line": "I don't really know anyone here. Weekends I mostly stay in my room.",
             "related_keys": ["relocation"], "reveal_hint": "When asked about friends, weekends or support."},
            {"key": "missed_promotion", "category": "Important Life Events", "label": "Missed a promotion", "importance": 2,
             "fact": "Was passed over for promotion three months ago, which he hasn't told anyone.",
             "patient_line": "Three months ago I didn't get the promotion. I haven't told anyone that, actually.",
             "related_keys": ["work_pressure", "self_doubt"], "reveal_hint": "Hesitant; needs trust."},
            {"key": "avoids_talking", "category": "Patient Needs", "label": "Needs a safe space to talk", "importance": 2,
             "fact": "Avoids discussing personal problems and needs to feel safe before opening up.",
             "patient_line": "I'm not used to talking about this stuff. It's kind of a relief to just say it.",
             "related_keys": [], "reveal_hint": "Emerges when the player is warm and patient."},
        ],
    },
    {
        "name": "Ananya Iyer", "age": 31, "occupation": "Primary School Teacher",
        "look": {"gender": "woman", "skin": 3, "hair": "long", "hair_color": "black", "outfit": "#8C5A6E", "glasses": False},
        "presenting_concern": "I can't switch off at night. My mind keeps racing and I wake up already tired. My husband says I've been snapping at everyone.",
        "reported_symptoms": ["Trouble sleeping", "Racing thoughts", "Irritability"],
        "personality": "Warm, organised, caretaker; feels guilty taking time for herself.",
        "communication_style": "Talks a lot about others; steers away from her own feelings.",
        "openness": "medium",
        "background": "Teacher for 8 years in Chennai. Primary carer for her mother who had a stroke last year.",
        "emotional_concerns": ["Guilt", "Resentment she feels ashamed of"],
        "underlying_concerns": ["Caregiver burnout", "No space for her own needs"],
        "life_events": ["Mother's stroke last year", "Took on extra classes to cover a colleague"],
        "relationships": "Supportive but busy husband; brother abroad who offers advice but no practical help.",
        "session_objective": "Understand what's behind Ananya's sleep problems and irritability, and identify supportive next steps.",
        "possible_next_steps": ["Explore sharing caregiving responsibilities", "Introduce boundaries and rest",
                                "Address guilt around her own needs", "Sleep routine support"],
        "discovery_facts": [
            {"key": "caregiving", "category": "Important Life Events", "label": "Caring for her mother", "importance": 3,
             "fact": "Became the primary carer for her mother after a stroke last year.",
             "patient_line": "My mother had a stroke last year, and since then I've been looking after her.",
             "related_keys": ["burnout", "brother"], "reveal_hint": "When asked about home or recent changes."},
            {"key": "extra_classes", "category": "Symptoms and Experiences", "label": "Extra workload at school", "importance": 1,
             "fact": "Took on extra classes to cover for a colleague on leave.",
             "patient_line": "I'm also covering extra classes at school because a colleague is on leave.",
             "related_keys": [], "reveal_hint": "When asked about work."},
            {"key": "guilt", "category": "Emotional State", "label": "Guilt about wanting rest", "importance": 2,
             "fact": "Feels guilty whenever she takes time for herself.",
             "patient_line": "If I sit down for even ten minutes I feel guilty, like I'm being selfish.",
             "related_keys": ["resentment"], "reveal_hint": "When asked how she feels or about time for herself."},
            {"key": "resentment", "category": "Underlying Concerns", "label": "Hidden resentment", "importance": 3,
             "fact": "Feels resentment toward her brother and is ashamed of it.",
             "patient_line": "I hate saying this, but I feel angry. Like, why is it always me? And then I feel terrible for thinking that.",
             "related_keys": ["brother", "guilt"], "reveal_hint": "Only with strong trust and non-judgement."},
            {"key": "brother", "category": "Relationships and Social Environment", "label": "Brother abroad doesn't help", "importance": 2,
             "fact": "Her brother lives abroad and gives advice but no practical help.",
             "patient_line": "My brother is in Canada. He calls with advice but he's not here doing any of it.",
             "related_keys": ["resentment", "caregiving"], "reveal_hint": "When asked about family support."},
            {"key": "burnout", "category": "Underlying Concerns", "label": "Caregiver burnout", "importance": 3,
             "fact": "Is running on empty with no space for her own needs — classic caregiver burnout.",
             "patient_line": "I think I'm just... empty. There's nothing left for me at the end of the day.",
             "related_keys": ["caregiving"], "reveal_hint": "After discussing caregiving with empathy."},
            {"key": "needs_permission", "category": "Patient Needs", "label": "Needs permission to rest", "importance": 2,
             "fact": "Needs to hear that her own needs matter too.",
             "patient_line": "Maybe I just need someone to tell me it's okay to need a break.",
             "related_keys": ["guilt"], "reveal_hint": "Toward the end if she feels understood."},
        ],
    },
    {
        "name": "Vikram Singh", "age": 47, "occupation": "Restaurant Owner",
        "look": {"gender": "man", "skin": 2, "hair": "buzz", "hair_color": "dark", "outfit": "#56606B", "beard": True},
        "presenting_concern": "My wife made me come. I'm fine, really. Just a bit short-tempered lately and not sleeping great.",
        "reported_symptoms": ["Irritability", "Poor sleep"],
        "personality": "Proud, guarded, practical; dislikes 'talking about feelings'.",
        "communication_style": "Deflects with jokes and business talk; tests whether the therapist is genuine.",
        "openness": "low",
        "background": "Built his restaurant from scratch 15 years ago in Delhi. Sees himself as the family's provider.",
        "emotional_concerns": ["Shame", "Fear of failure"],
        "underlying_concerns": ["Identity tied to being the provider", "Unprocessed grief"],
        "life_events": ["Restaurant revenue fell sharply this year", "Father died two years ago"],
        "relationships": "Married with two teenagers; growing distance with his wife.",
        "session_objective": "Build enough trust to understand what's behind Vikram's irritability and agree on next steps.",
        "possible_next_steps": ["Continue building trust over sessions", "Explore grief for his father",
                                "Discuss financial stress and practical support", "Involve spouse when ready"],
        "discovery_facts": [
            {"key": "business_trouble", "category": "Symptoms and Experiences", "label": "Business is struggling", "importance": 2,
             "fact": "Restaurant revenue fell sharply this year and he may need to take a loan.",
             "patient_line": "Business is down. A lot. I might have to take a loan, which I swore I'd never do.",
             "related_keys": ["provider_identity"], "reveal_hint": "When asked about work, after some rapport."},
            {"key": "hiding_from_wife", "category": "Relationships and Social Environment", "label": "Hiding finances from wife", "importance": 2,
             "fact": "Hasn't told his wife how bad the finances are.",
             "patient_line": "My wife doesn't know how bad it is. I don't want her worrying.",
             "related_keys": ["business_trouble"], "reveal_hint": "When asked about his marriage."},
            {"key": "provider_identity", "category": "Underlying Concerns", "label": "Identity as the provider", "importance": 3,
             "fact": "His self-worth is tied to being the family's provider; failing feels like failing as a man.",
             "patient_line": "A man provides for his family. If I can't do that, what am I?",
             "related_keys": ["business_trouble", "father_death"], "reveal_hint": "Only with trust."},
            {"key": "father_death", "category": "Important Life Events", "label": "Father died two years ago", "importance": 3,
             "fact": "His father died two years ago and he never took time to grieve.",
             "patient_line": "My father passed two years ago. I went back to work the next week. Someone had to.",
             "related_keys": ["grief"], "reveal_hint": "When asked about family or losses."},
            {"key": "grief", "category": "Underlying Concerns", "label": "Unprocessed grief", "importance": 3,
             "fact": "Unprocessed grief for his father fuels his anger.",
             "patient_line": "I never really... I never cried for him. Maybe that's what all this anger is.",
             "related_keys": ["father_death"], "reveal_hint": "Deep trust only."},
            {"key": "teen_distance", "category": "Relationships and Social Environment", "label": "Distance from his kids", "importance": 1,
             "fact": "His teenagers avoid him because of his temper.",
             "patient_line": "My kids kind of disappear when I come home. I see it.",
             "related_keys": [], "reveal_hint": "When asked about home life."},
        ],
    },
]


def generate_patient(level: int, avoid_names: list[str] | None = None) -> PatientProfileLLM:
    """Starts at the template matching the level tier, then rotates to one not seen recently."""
    start = 0 if level <= 3 else (1 if level <= 6 else 2)
    recent = (avoid_names or [])[:len(TEMPLATES) - 1]
    for i in range(len(TEMPLATES)):
        t = TEMPLATES[(start + i) % len(TEMPLATES)]
        if t["name"] not in recent:
            return PatientProfileLLM.model_validate(t)
    return PatientProfileLLM.model_validate(TEMPLATES[start])


def _fact_score(fact: dict, question: set[str]) -> float:
    pool = words(" ".join([fact["label"], fact["fact"], fact["category"], fact.get("reveal_hint", "")]))
    return len(question & pool)


def simulate_reply(profile: dict, history: list[dict], discovered_keys: set[str], player_msg: str) -> str:
    q = words(player_msg)
    low = player_msg.lower()
    empathic = any(e in low for e in EMPATHY)
    rapport = sum(1 for m in history if m["role"] == "player" and any(e in m["content"].lower() for e in EMPATHY))
    candidates = [f for f in profile["discovery_facts"] if f["key"] not in discovered_keys]
    if not candidates:
        return "I think I've told you most of it now. It feels good to have said it out loud."
    scored = sorted(candidates, key=lambda f: (_fact_score(f, q), -f["importance"]), reverse=True)
    best = scored[0]
    needed_rapport = {1: 0, 2: 0, 3: 1}[best["importance"]] + (1 if profile.get("openness") == "low" else 0)
    opener = random.choice(["Hmm.", "Well...", "I guess...", "Okay.", ""]) if not empathic else random.choice(
        ["Thanks for saying that.", "That actually helps.", "Yeah..."])
    if _fact_score(best, q) == 0 and not empathic:
        return f"{opener} I'm not sure what you mean. {profile['presenting_concern'].split('.')[0]}.".strip()
    if rapport + (1 if empathic else 0) < needed_rapport:
        return f"{opener} I'd rather not get into that right now. It's... a lot.".strip()
    line = best.get("patient_line") or best["fact"]
    return f"{opener} {line}".strip()


CATEGORY_EMOTION = {"Emotional State": "sad", "Underlying Concerns": "tearful", "Important Life Events": "sad",
                    "Relationships and Social Environment": "sad", "Symptoms and Experiences": "anxious",
                    "Patient Needs": "relieved", "Personal Background": "neutral"}


def simulate_turn(profile: dict, history: list[dict], discovered_keys: set[str], player_msg: str,
                  comfort: int) -> PatientTurnLLM:
    line = simulate_reply(profile, history, discovered_keys, player_msg)
    empathic = any(e in player_msg.lower() for e in EMPATHY)
    new_comfort = max(0, min(100, comfort + (8 if empathic else -2)))
    revealed = next((f for f in profile["discovery_facts"]
                     if f.get("patient_line") and f["patient_line"][:40].lower() in line.lower()), None)
    if revealed:
        emotion = CATEGORY_EMOTION.get(revealed["category"], "neutral")
    elif "rather not" in line:
        emotion = "guarded"
    elif "not sure" in line:
        emotion = "anxious" if profile.get("openness") != "low" else "guarded"
    else:
        emotion = "relieved" if "told you most" in line else "neutral"
    return PatientTurnLLM(line=line, emotion=emotion, comfort=new_comfort)


def detect(profile: dict, undiscovered: list[dict], patient_reply: str) -> list[dict]:
    out = []
    reply = patient_reply.lower()
    for f in undiscovered:
        line = (f.get("patient_line") or "").lower()
        if line and line[:40] in reply:
            out.append({"key": f["key"], "confidence": 0.95, "evidence": f.get("patient_line", "")[:160]})
    return out


def evaluate(profile: dict, transcript: list[dict], discovered_keys: set[str], assessment: dict) -> SessionEvaluationLLM:
    player = [m["content"] for m in transcript if m["role"] == "player"]
    n = max(len(player), 1)
    emp = sum(1 for p in player if any(e in p.lower() for e in EMPATHY)) / n
    open_q = sum(1 for p in player if any(p.lower().startswith(o) or f" {o} " in p.lower() for o in OPEN_Q)) / n
    facts = profile["discovery_facts"]
    coverage = len(discovered_keys) / max(len(facts), 1)
    a_words = words(" ".join(assessment.values()))
    hidden = words(" ".join(profile["underlying_concerns"] + profile["emotional_concerns"]
                            + [f["fact"] for f in facts]))
    acc = min(1.0, len(a_words & hidden) / 12)
    steps = min(1.0, len(a_words & words(" ".join(profile["possible_next_steps"]))) / 5)

    def s(x: float, base: float = 35) -> float:
        return round(max(0, min(100, base + x * (100 - base))), 1)

    cs = CategoryScores(
        empathy_rapport=s(emp), question_relevance=s(open_q * 0.5 + coverage * 0.5),
        active_listening=s((emp + coverage) / 2), understanding_symptoms=s(coverage * 0.6 + acc * 0.4),
        underlying_concerns=s(acc), next_steps=s(steps),
    )
    sat_base = s(emp * 0.7 + 0.3 * coverage, 45)
    sat = SatisfactionBreakdown(feeling_heard=sat_base, empathy=s(emp, 40), respect=s(0.8, 50), comfort=sat_base,
                                trust=s(coverage, 40), feeling_understood=s(acc, 40))
    und = UnderstandingLLM(assessment_accuracy=s(acc, 20), connections_identified=s(acc * coverage, 20),
                           uncertainty_recognition=60, prioritization=s(acc, 30))
    strengths, improvements = [], []
    (strengths if emp > 0.3 else improvements).append(
        "You validated the patient's feelings regularly." if emp > 0.3 else "Reflect and validate feelings more often to build trust.")
    (strengths if open_q > 0.4 else improvements).append(
        "Good use of open-ended questions." if open_q > 0.4 else "Use more open-ended questions (\"how\", \"what\", \"tell me about\").")
    if coverage < 0.6:
        improvements.append("Several important parts of the patient's story were never uncovered.")
    else:
        strengths.append("You uncovered most of the patient's story.")
    return SessionEvaluationLLM(category_scores=cs, satisfaction=sat, understanding=und, strengths=strengths,
                                improvements=improvements,
                                summary="(Offline demo evaluation — connect Grok for detailed, semantic feedback.)")


def summarize(messages: list[dict]) -> str:
    return " ".join(f"{m['role']}: {m['content'][:80]}" for m in messages)[-1500:]
