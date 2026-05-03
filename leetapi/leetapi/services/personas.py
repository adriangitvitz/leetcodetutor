from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PersonaKey = Literal["scholar", "coach", "sage", "hacker"]


@dataclass(frozen=True)
class Persona:
    key: PersonaKey
    name: str
    desc: str
    opener_teach: str
    opener_soc: str
    opener_chat: str


PERSONAS: dict[PersonaKey, Persona] = {
    "scholar": Persona(
        key="scholar",
        name="The Scholar",
        desc="Precise, structured, formal",
        opener_teach="Let us proceed methodically. This problem rewards careful observation over clever tricks.",
        opener_soc="Consider the problem carefully before answering. I will ask, you will think.",
        opener_chat="Ask your question — I will answer with precision.",
    ),
    "coach": Persona(
        key="coach",
        name="The Coach",
        desc="Encouraging, energetic",
        opener_teach="Okay! Great problem — let's break it down together. You've got this.",
        opener_soc="Love it, we're warming up. Tell me what you see — first instinct counts.",
        opener_chat="Hit me with a question! Any question, no bad ones.",
    ),
    "sage": Persona(
        key="sage",
        name="The Sage",
        desc="Socratic, patient, zen",
        opener_teach="Before we solve — let us understand. Patterns are more useful than answers.",
        opener_soc="There are no wrong answers here; only discoveries.",
        opener_chat="Speak your thought. We shall think together.",
    ),
    "hacker": Persona(
        key="hacker",
        name="The Hacker",
        desc="Terse, pragmatic, code-first",
        opener_teach="Reading the statement once. Building intuition. Writing the code. That's the order.",
        opener_soc="What's the smallest failing case? Start there.",
        opener_chat="Ask. I'll be brief.",
    ),
}


def is_valid_persona(value: str) -> bool:
    return value in PERSONAS
