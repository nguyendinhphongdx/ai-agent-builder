"""Unit tests for the workflow runner topology helpers.

These don't need a DB — they operate on plain SQLAlchemy model instances
constructed in-memory.
"""
from __future__ import annotations

from collections import namedtuple

from app.workflows.runner import WorkflowRunner

# Lightweight stand-in for WorkflowEdge — we only need source/target.
Edge = namedtuple("Edge", ["source_node_id", "target_node_id", "source_handle", "target_handle"])


def test_build_adjacency_groups_by_source():
    edges = [
        Edge("a", "b", None, None),
        Edge("a", "c", None, None),
        Edge("b", "d", "true", None),
    ]
    adj = WorkflowRunner._build_adjacency(edges)
    assert sorted(adj["a"]) == [("b", None), ("c", None)]
    assert adj["b"] == [("d", "true")]


def test_reverse_adjacency_for_upstream_walk():
    """Reverse adjacency drives 'who feeds into me' lookups — used by
    expression context (nodes['X']) and merge-input gathering."""
    edges = [
        Edge("a", "c", None, None),
        Edge("b", "c", None, None),
        Edge("c", "d", None, None),
    ]
    rev = WorkflowRunner._build_reverse_adjacency(edges)
    parents_of_c = {src for src, _ in rev["c"]}
    assert parents_of_c == {"a", "b"}
    assert {src for src, _ in rev["d"]} == {"c"}
