from __future__ import annotations

from collections.abc import Iterable

TOPIC_GROUPS: dict[str, list[str]] = {
    "Linked Lists":         ["Linked List", "Doubly-Linked List"],
    "Trees":                ["Tree", "Binary Tree", "Depth-First Search", "Breadth-First Search"],
    "Graphs":               ["Graph", "Union Find", "Topological Sort"],
    "Dynamic Programming":  ["Dynamic Programming", "Memoization"],
    "Arrays":               ["Array", "Matrix", "Prefix Sum"],
    "Strings":              ["String", "Sliding Window"],
    "Hash Tables":          ["Hash Table"],
    "Two Pointers":         ["Two Pointers"],
    "Stacks":               ["Stack", "Monotonic Stack"],
    "Heaps":                ["Heap (Priority Queue)"],
    "Binary Search":        ["Binary Search"],
    "Backtracking":         ["Backtracking", "Recursion"],
    "Greedy":               ["Greedy"],
    "Design":               ["Design"],
    "Bit":                  ["Bit Manipulation"],
}


def split_tags(topics_str: str) -> list[str]:
    if not topics_str:
        return []
    return [t.strip() for t in topics_str.split(",") if t.strip()]


def groups_for_tags(tags: Iterable[str]) -> list[str]:
    tag_set = set(tags)
    return [
        name
        for name, members in TOPIC_GROUPS.items()
        if tag_set.intersection(members)
    ]


def top_topic_from_weighted_tags(
    weighted: Iterable[tuple[str, float]],
) -> tuple[str | None, float]:
    tally: dict[str, float] = {}
    for topics_str, weight in weighted:
        for group in groups_for_tags(split_tags(topics_str)):
            tally[group] = tally.get(group, 0.0) + float(weight)
    if not tally:
        return None, 0.0
    order = {name: i for i, name in enumerate(TOPIC_GROUPS)}
    best = min(tally.items(), key=lambda kv: (-kv[1], order.get(kv[0], 1_000_000)))
    return best[0], best[1]
