import type { Persona } from "./types";

export const PERSONAS: Record<Persona["key"], Persona> = {
  scholar: {
    key: "scholar",
    name: "The Scholar",
    desc: "Precise, structured, formal",
    openerTeach: "Let us proceed methodically. This problem rewards careful observation over clever tricks.",
    openerSoc: "Consider the problem carefully before answering. I will ask, you will think.",
    openerChat: "Ask your question - I will answer with precision.",
  },
  coach: {
    key: "coach",
    name: "The Coach",
    desc: "Encouraging, energetic",
    openerTeach: "Okay! Great problem - let's break it down together. You've got this.",
    openerSoc: "Love it, we're warming up. Tell me what you see - first instinct counts.",
    openerChat: "Hit me with a question! Any question, no bad ones.",
  },
  sage: {
    key: "sage",
    name: "The Sage",
    desc: "Socratic, patient, zen",
    openerTeach: "Before we solve - let us understand. Patterns are more useful than answers.",
    openerSoc: "There are no wrong answers here; only discoveries.",
    openerChat: "Speak your thought. We shall think together.",
  },
  hacker: {
    key: "hacker",
    name: "The Hacker",
    desc: "Terse, pragmatic, code-first",
    openerTeach: "Reading the statement once. Building intuition. Writing the code. That's the order.",
    openerSoc: "What's the smallest failing case? Start there.",
    openerChat: "Ask. I'll be brief.",
  },
};
