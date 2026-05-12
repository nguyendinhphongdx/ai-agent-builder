"""Unit tests for the workflow expression evaluator.

Pure tests — no DB, no FastAPI. Highest-leverage module to cover because
it parses user templates at execution time and ships output to LLM
prompts / tool args / HTTP request bodies.
"""
from __future__ import annotations

import pytest

from app.modules.workflows.expression import evaluate_template
from app.modules.workflows.template_utils import render_template

# ─── Backward compat with the legacy {{key}} syntax ───────────────────


def test_legacy_simple_substitution():
    assert render_template("Hello {{name}}", {"name": "Alice"}) == "Hello Alice"


def test_legacy_nested_dot_path():
    assert (
        render_template("{{user.email}}", {"user": {"email": "a@b.com"}})
        == "a@b.com"
    )


def test_legacy_missing_returns_empty_string():
    """Old shim returns '' for missing names — preserves contract for
    callers that still concat the result into a larger string."""
    assert render_template("{{ missing }}", {"a": 1}) == ""


# ─── New API: pure expression preserves type ──────────────────────────


def test_pure_expression_preserves_int():
    assert evaluate_template("{{ json.x }}", item={"x": 42}) == 42


def test_pure_expression_preserves_list():
    out = evaluate_template("{{ items }}", items=[{"a": 1}, {"a": 2}])
    assert isinstance(out, list)
    assert len(out) == 2


def test_mixed_template_returns_string():
    assert evaluate_template("Count: {{ json.x }}", item={"x": 42}) == "Count: 42"


def test_pure_missing_returns_none():
    """Pure expr path returns raw None (caller decides what to do).
    Mixed template path coerces None → ''."""
    assert evaluate_template("{{ missing }}", item={"a": 1}) is None
    assert evaluate_template("Hello {{ missing }}", item={"a": 1}) == "Hello "


# ─── Upstream node references ─────────────────────────────────────────


def test_nodes_lookup_by_label():
    upstream = {"LLM": [{"text": "hi"}]}
    assert evaluate_template('{{ nodes["LLM"][0].text }}', upstream=upstream) == "hi"


def test_vars_dot_access():
    assert (
        evaluate_template("{{ vars.email }}", variables={"email": "x@y.com"})
        == "x@y.com"
    )


def test_ternary_expression():
    assert (
        evaluate_template(
            '{{ "many" if json.x > 10 else "few" }}', item={"x": 20}
        )
        == "many"
    )


def test_real_chaining_scenario():
    """End-to-end: agent → template node references upstream output."""
    upstream = {"GenerateGreeting": [{"response": "Hello there"}]}
    result = evaluate_template(
        'Reply: {{ nodes["GenerateGreeting"][0].response }}',
        item={},
        upstream=upstream,
    )
    assert result == "Reply: Hello there"


# ─── Sandbox ──────────────────────────────────────────────────────────


def test_sandbox_blocks_import():
    """Sandboxed evaluator must refuse __import__ — would let an LLM
    template escape into the host process."""
    # Should not raise out of evaluate_template — the inner eval raises
    # but evaluate_expression catches NameNotDefined / similar. For
    # unknown builtins like __import__, simpleeval raises FunctionNotDefined,
    # which is NOT in our catch list, so it propagates.
    with pytest.raises(Exception):
        evaluate_template('{{ __import__("os") }}', item={})


def test_sandbox_blocks_open():
    with pytest.raises(Exception):
        evaluate_template('{{ open("/etc/passwd") }}', item={})


# ─── Backcompat shadow protection ─────────────────────────────────────


def test_legacy_keys_dont_shadow_new_api():
    """Item with a key called 'json' or 'nodes' must NOT shadow the
    canonical names — that would silently break templates after the
    schema of upstream data changes."""
    item = {"json": "broken", "nodes": "also-broken", "x": 5}
    upstream = {"X": [{"value": "ok"}]}

    # `json.x` should resolve via canonical, not via item['json']
    assert evaluate_template("{{ json.x }}", item=item) == 5
    # `nodes["X"]` resolves via canonical
    assert (
        evaluate_template('{{ nodes["X"][0].value }}', item=item, upstream=upstream)
        == "ok"
    )
