"""Unit tests for topic grouping (no DB)."""

from __future__ import annotations

from leetapi.services.topics import (
    TOPIC_GROUPS,
    groups_for_tags,
    split_tags,
    top_topic_from_weighted_tags,
)


def test_split_tags_handles_spaces_and_empties():
    assert split_tags("Array, Hash Table") == ["Array", "Hash Table"]
    assert split_tags("Array,, ") == ["Array"]
    assert split_tags("") == []
    assert split_tags(None) == []  # type: ignore[arg-type]


def test_groups_for_tags_maps_through_topic_groups():
    # "Linked List" → "Linked Lists" group
    assert "Linked Lists" in groups_for_tags(["Linked List", "Hash Table"])
    # "Hash Table" → "Hash Tables"
    assert "Hash Tables" in groups_for_tags(["Linked List", "Hash Table"])


def test_groups_for_tags_finds_trees_via_dfs_alias():
    """Trees group includes both Tree and Depth-First Search aliases."""
    assert "Trees" in groups_for_tags(["Depth-First Search"])


def test_top_topic_picks_highest_summed_weight():
    # Two-Sum-shaped row (Array, Hash Table) at weight 70 + LRU Cache
    # (Linked List, Hash Table) at weight 92 → Linked Lists wins because
    # 92 > 70+0 for that group; Hash Tables totals 70+92=162 wins overall.
    weighted = [
        ("Array, Hash Table", 70),
        ("Linked List, Doubly-Linked List, Hash Table", 92),
    ]
    name, score = top_topic_from_weighted_tags(weighted)
    assert name == "Hash Tables"
    assert score == 162


def test_top_topic_breaks_ties_by_topic_groups_insertion_order():
    """When two groups tie, earlier-defined groups in TOPIC_GROUPS win."""
    weighted = [("Linked List", 10), ("Tree", 10)]
    name, _ = top_topic_from_weighted_tags(weighted)
    # Linked Lists is defined before Trees in TOPIC_GROUPS.
    assert list(TOPIC_GROUPS).index(name) == 0
    assert name == "Linked Lists"


def test_top_topic_returns_none_on_empty():
    assert top_topic_from_weighted_tags([]) == (None, 0.0)
