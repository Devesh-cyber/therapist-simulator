"""Levels, difficulty tiers and XP rules."""

DIFFICULTY_TIERS = [(3, "Beginner"), (6, "Intermediate"), (9, "Advanced"), (15, "Expert")]
DIFFICULTY_MULTIPLIER = {"Beginner": 1.0, "Intermediate": 1.25, "Advanced": 1.5, "Expert": 1.75, "Master": 2.0}


def difficulty_for_level(level: int) -> str:
    for max_level, name in DIFFICULTY_TIERS:
        if level <= max_level:
            return name
    return "Master"


def xp_required(level: int) -> int:
    """Total XP needed to reach `level`. L1=0, L2=100, L3=300, L4=600, ..."""
    return 50 * (level - 1) * level


def level_for_xp(xp: int) -> int:
    level = 1
    while xp >= xp_required(level + 1):
        level += 1
    return level


def xp_for_session(overall: float, understanding: float, satisfaction: float, difficulty: str,
                   coverage: float) -> int:
    """XP rewards performance, understanding and satisfaction, scaled by difficulty.
    Small bonus for full discovery; never negative."""
    base = 0.5 * overall + 0.25 * understanding + 0.25 * satisfaction  # 0..100
    bonus = 10 if coverage >= 0.999 else 0
    return max(5, round((base + bonus) * DIFFICULTY_MULTIPLIER.get(difficulty, 1.0)))


DIFFICULTY_GUIDE = {
    "Beginner": "One main concern with an obvious link to the symptoms. Patient is fairly open (openness high or medium). 6-7 discovery facts.",
    "Intermediate": "Two interconnected concerns. Patient is moderately guarded about the most personal facts (openness medium). 7-9 discovery facts.",
    "Advanced": "Several interconnected concerns, one of which the patient does not fully recognise themselves. Patient deflects sometimes (openness medium or low). 8-10 discovery facts.",
    "Expert": "Layered concerns with some ambiguity: the presenting concern is partly a cover for a deeper issue; some details seem to conflict until connected. Openness low. 9-11 discovery facts.",
    "Master": "Highly nuanced emotional situation with conflicting or incomplete self-reports, strong defences and subtle connections between facts. Openness low. 10-12 discovery facts.",
}
