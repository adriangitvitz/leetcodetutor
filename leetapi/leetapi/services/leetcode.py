from __future__ import annotations

import asyncio
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag
from fastapi import HTTPException
from markdownify import markdownify as html_to_md_lib
from sqlmodel.ext.asyncio.session import AsyncSession

from ..models import Statement

_statement_locks: dict[str, asyncio.Lock] = {}

def _statement_lock(slug: str) -> asyncio.Lock:
    lock = _statement_locks.get(slug)
    if lock is None:
        lock = asyncio.Lock()
        _statement_locks[slug] = lock
    return lock

GRAPHQL_URL = "https://leetcode.com/graphql/"
QUERY = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionFrontendId
    title
    titleSlug
    content
    difficulty
    hints
    topicTags { name }
  }
}
""".strip()

HEADING_EXAMPLE_RE = re.compile(r"^\s*example\s*\d*\s*[:.]?\s*$")
SLUG_RE = re.compile(r"^[a-z0-9-]+$")


def slug_from_input(value: str) -> str:
    """Accept a bare slug or a full LeetCode URL; return the slug."""
    value = value.strip()
    if value.startswith(("http://", "https://")):
        path = urlparse(value).path.strip("/").split("/")
        if "problems" in path:
            i = path.index("problems")
            if i + 1 < len(path):
                return path[i + 1]
        raise ValueError(f"Could not parse slug from URL: {value}")
    return value

async def fetch_question(slug: str, *, client: httpx.AsyncClient | None = None) -> dict:
    """Hit LeetCode's GraphQL API and return the `question` payload."""
    if not SLUG_RE.match(slug):
        raise HTTPException(status_code=400, detail=f"invalid slug: {slug!r}")

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (leetapi-fetcher)",
        "Referer": f"https://leetcode.com/problems/{slug}/",
    }
    payload = {
        "query": QUERY,
        "variables": {"titleSlug": slug},
        "operationName": "questionData",
    }

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=20.0, headers=headers)
    try:
        r = await client.post(GRAPHQL_URL, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
    finally:
        if own_client:
            await client.aclose()

    if data.get("errors"):
        raise HTTPException(status_code=502, detail=f"GraphQL errors: {data['errors']}")
    q = (data.get("data") or {}).get("question")
    if not q:
        raise HTTPException(status_code=404, detail=f"problem not found upstream: {slug}")
    if not q.get("content"):
        raise HTTPException(
            status_code=403,
            detail=f"problem '{slug}' is locked (premium) or has no content",
        )
    return q

def _heading_kind(el: Tag) -> str | None:
    """Classify a top-level element as a section boundary, if any."""
    if not isinstance(el, Tag):
        return None
    text = el.get_text(" ", strip=True).lower().rstrip(":").strip()
    if HEADING_EXAMPLE_RE.match(text):
        return "example"
    if text == "constraints":
        return "constraints"
    if text in {"follow-up", "follow up"}:
        return "follow_up"
    return None


def _preprocess_html(html: str) -> str:
    """Rewrite `<sup>`/`<sub>` so exponents survive markdownify (which drops them)."""
    html = re.sub(r"<sup>(.*?)</sup>", r"^\1", html, flags=re.DOTALL)
    html = re.sub(r"<sub>(.*?)</sub>", r"_\1", html, flags=re.DOTALL)
    return html


def _split_content(html: str) -> dict[str, list]:
    """Walk the HTML and split top-level nodes into description / examples /
    constraints / follow_up buckets."""
    html = _preprocess_html(html)
    soup = BeautifulSoup(html, "html.parser")
    nodes = [
        n
        for n in soup.children
        if not (isinstance(n, NavigableString) and not n.strip())
    ]

    description: list = []
    examples: list[list] = []
    constraints: list = []
    follow_up: list = []
    state = "description"
    current_example: list = []

    def flush_example() -> None:
        nonlocal current_example
        if current_example:
            examples.append(current_example)
            current_example = []

    for el in nodes:
        kind = _heading_kind(el)
        if kind == "example":
            flush_example()
            state = "example"
            continue  # drop the header itself; we render our own
        if kind == "constraints":
            flush_example()
            state = "constraints"
            continue
        if kind == "follow_up":
            flush_example()
            state = "follow_up"
            continue

        if state == "description":
            description.append(el)
        elif state == "example":
            current_example.append(el)
        elif state == "constraints":
            constraints.append(el)
        elif state == "follow_up":
            follow_up.append(el)

    flush_example()
    return {
        "description": description,
        "examples": examples,
        "constraints": constraints,
        "follow_up": follow_up,
    }


def _nodes_to_md(nodes: list) -> str:
    html = "".join(str(n) for n in nodes)
    if not html.strip():
        return ""
    text = html_to_md_lib(html, heading_style="ATX", bullets="-")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def build_markdown(question: dict) -> str:
    sections = _split_content(question["content"])
    tags = ", ".join(t["name"] for t in (question.get("topicTags") or [])) or "—"

    lines: list[str] = [
        f"# {question['questionFrontendId']}. {question['title']}",
        "",
        f"**Difficulty:** {question['difficulty']}  ",
        f"**Tags:** {tags}  ",
        f"**Link:** https://leetcode.com/problems/{question['titleSlug']}/",
        "",
    ]

    desc = _nodes_to_md(sections["description"])
    if desc:
        lines += ["## Description", "", desc, ""]

    if sections["examples"]:
        lines += ["## Examples", ""]
        for i, ex_nodes in enumerate(sections["examples"], start=1):
            lines += [f"### Example {i}", "", _nodes_to_md(ex_nodes), ""]

    cons = _nodes_to_md(sections["constraints"])
    if cons:
        lines += ["## Constraints", "", cons, ""]

    fu = _nodes_to_md(sections["follow_up"])
    if fu:
        lines += ["## Follow-up", "", fu, ""]

    hints = question.get("hints") or []
    if hints:
        lines += ["## Hints", ""]
        for i, hint_html in enumerate(hints, start=1):
            hint_md = html_to_md_lib(
                _preprocess_html(hint_html), heading_style="ATX", bullets="-"
            ).strip()
            hint_md = hint_md.replace("\n", "\n   ")
            lines.append(f"{i}. {hint_md}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"

def parse_statement(md: str) -> dict:
    lines = md.replace("\r\n", "\n").split("\n")

    number: int | None = None
    for line in lines:
        m = re.match(r"^#\s+(\d+)\.\s+", line)
        if m:
            number = int(m.group(1))
            break
        if line.startswith("# "):
            break  # title found, no number

    sections = _slice_md_sections(lines)
    description = "\n".join(sections.get("Description", [])).strip()
    examples = _parse_examples(sections.get("Examples", []))
    constraints = _parse_constraints(sections.get("Constraints", []))

    return {
        "number": number,
        "description": description,
        "examples": examples,
        "constraints": constraints,
    }


def _slice_md_sections(lines: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    current: str | None = None
    buf: list[str] = []

    def flush():
        nonlocal buf
        if current is not None:
            out[current] = buf
        buf = []

    for line in lines:
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            flush()
            current = m.group(1)
            continue
        if current is not None:
            buf.append(line)
    flush()
    return out


_EXAMPLE_HEADER_RE = re.compile(r"^###\s+Example\s+\d+", re.IGNORECASE)
_MARKER_RE = re.compile(
    r"^\s*\*{0,2}(Input|Output|Explanation)\*{0,2}\s*[:：]\s*\*{0,2}\s*(.*?)\s*\*{0,2}\s*$",
    re.IGNORECASE,
)

def _parse_examples(lines: list[str]) -> list[dict]:
    examples: list[dict] = []
    chunks: list[list[str]] = []
    current: list[str] = []
    seen_header = False

    for line in lines:
        if _EXAMPLE_HEADER_RE.match(line):
            if seen_header:
                chunks.append(current)
            current = []
            seen_header = True
            continue
        if seen_header:
            current.append(line)

    if seen_header:
        chunks.append(current)

    for chunk in chunks:
        parsed = _parse_example_block("\n".join(chunk))
        if parsed["input"] or parsed["output"]:
            examples.append(parsed)
    return examples


def _parse_example_block(block: str) -> dict:
    sections: dict[str, list[str]] = {"Input": [], "Output": [], "Explanation": []}
    key: str | None = None
    in_fence = False

    for raw in block.split("\n"):
        stripped = raw.strip()

        if stripped.startswith("```"):
            in_fence = not in_fence
            continue

        m = _MARKER_RE.match(raw)
        if m:
            key = m.group(1).capitalize()
            tail = m.group(2).strip()
            if tail:
                sections[key].append(tail)
            continue

        if key:
            sections[key].append(raw)

    def trim(xs: list[str]) -> str:
        while xs and not xs[0].strip():
            xs.pop(0)
        while xs and not xs[-1].strip():
            xs.pop()
        return "\n".join(xs).strip()

    out: dict = {"input": trim(sections["Input"]), "output": trim(sections["Output"])}
    expl = trim(sections["Explanation"])
    if expl:
        out["explanation"] = expl
    return out


def _parse_constraints(lines: list[str]) -> list[str]:
    out: list[str] = []
    for raw in lines:
        m = re.match(r"^\s*-\s+(.*)$", raw)
        if m and m.group(1).strip():
            out.append(m.group(1).strip())
    return out

async def ensure_statement(
    session: AsyncSession,
    slug: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> Statement:
    existing = await session.get(Statement, slug)
    if existing is not None:
        return existing

    async with _statement_lock(slug):
        existing = await session.get(Statement, slug)
        if existing is not None:
            return existing

        question = await fetch_question(slug, client=client)
        md = build_markdown(question)
        row = Statement(slug=slug, content=md)
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row
