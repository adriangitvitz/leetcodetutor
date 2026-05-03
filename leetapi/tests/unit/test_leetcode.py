"""Unit tests for `services/leetcode.py` — pure HTML→MD and MD→sections.

The fixture is a real-shaped LeetCode GraphQL response for `two-sum`.
"""

from __future__ import annotations

import json
from pathlib import Path

from leetapi.services.leetcode import (
    build_markdown,
    parse_statement,
    slug_from_input,
)

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "leetcode_two_sum.json"


def _question() -> dict:
    return json.loads(FIXTURE.read_text())["data"]["question"]


# ---------- slug parsing ------------------------------------------------


def test_slug_from_input_passes_through_bare_slug():
    assert slug_from_input("two-sum") == "two-sum"


def test_slug_from_input_extracts_from_url():
    assert slug_from_input("https://leetcode.com/problems/two-sum/") == "two-sum"
    assert slug_from_input("https://leetcode.com/problems/two-sum") == "two-sum"


# ---------- build_markdown ----------------------------------------------


def test_build_markdown_includes_title_and_meta():
    md = build_markdown(_question())
    assert md.startswith("# 1. Two Sum")
    assert "**Difficulty:** Easy" in md
    assert "**Tags:** Array, Hash Table" in md
    assert "**Link:** https://leetcode.com/problems/two-sum/" in md


def test_build_markdown_has_section_headers():
    md = build_markdown(_question())
    assert "## Description" in md
    assert "## Examples" in md
    assert "### Example 1" in md
    assert "### Example 2" in md
    assert "## Constraints" in md
    assert "## Follow-up" in md
    assert "## Hints" in md


def test_build_markdown_preserves_exponents_via_sup_replacement():
    """`<sup>4</sup>` should render as `^4` (markdownify drops <sup> by default)."""
    md = build_markdown(_question())
    assert "10^4" in md
    assert "10^9" in md


# ---------- parse_statement ---------------------------------------------


def test_parse_statement_extracts_number_and_description():
    md = build_markdown(_question())
    parsed = parse_statement(md)
    assert parsed["number"] == 1
    assert "Given an array of integers" in parsed["description"]


def test_parse_statement_extracts_examples_with_io():
    md = build_markdown(_question())
    parsed = parse_statement(md)
    assert len(parsed["examples"]) == 2
    ex1 = parsed["examples"][0]
    assert "nums = [2,7,11,15]" in ex1["input"]
    assert ex1["output"] == "[0,1]"
    assert "we return [0, 1]" in (ex1.get("explanation") or "")
    # Example 2 has no explanation.
    assert parsed["examples"][1].get("explanation") in (None, "")


def test_parse_statement_extracts_constraints_as_bullets():
    md = build_markdown(_question())
    parsed = parse_statement(md)
    assert len(parsed["constraints"]) == 4
    assert any("nums.length" in c for c in parsed["constraints"])


# ---------- new LeetCode format (count-and-say) -------------------------
#
# Real LeetCode HTML for problems added/refreshed in the last couple of years
# uses a different example layout: a <div class="example-block"> wrapping
# separate <p><strong>Input:</strong>…</p> / <p><strong>Output:</strong>…</p>
# / <p><strong>Explanation:</strong></p> paragraphs, optionally followed by
# a <pre> with the explanation body. The OLD layout (single <pre> with
# Input:/Output:/Explanation: lines) still appears on classic problems like
# Two Sum. The parser must handle both.

CAS_FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "leetcode_count_and_say.json"


def _cas_question() -> dict:
    return json.loads(CAS_FIXTURE.read_text())["data"]["question"]


def test_count_and_say_examples_have_input_and_output():
    md = build_markdown(_cas_question())
    parsed = parse_statement(md)
    assert len(parsed["examples"]) == 2

    ex1, ex2 = parsed["examples"]
    assert ex1["input"] == "n = 4"
    assert ex1["output"] == '"1211"'
    # The fenced explanation body becomes the explanation field.
    assert "countAndSay(4)" in (ex1.get("explanation") or "")

    assert ex2["input"] == "n = 1"
    assert ex2["output"] == '"1"'
    assert ex2.get("explanation") == "This is the base case."


def test_count_and_say_constraints_extracted():
    md = build_markdown(_cas_question())
    parsed = parse_statement(md)
    assert parsed["constraints"] == ["`1 <= n <= 30`"]


def test_count_and_say_does_not_lose_example_two_when_first_has_fence():
    """Regression: the old parser walked fence-by-fence, so Example 2
    (which has a plain <p> explanation, no <pre>) was silently dropped
    while Example 1's fence got mis-attributed."""
    md = build_markdown(_cas_question())
    parsed = parse_statement(md)
    inputs = [e["input"] for e in parsed["examples"]]
    assert inputs == ["n = 4", "n = 1"]
