"""Metrics registry tests — works with or without prometheus_client."""
from __future__ import annotations

from xtv_support.infrastructure.metrics.registry import (
    counter,
    get_registry,
    histogram,
    render_text,
)


def test_counter_returns_a_metric_or_noop() -> None:
    m = counter("test_counter_total", "description")
    # Accepts label + inc without crashing regardless of prom availability.
    m.labels(label="x") if hasattr(m, "labels") else None
    m.inc() if hasattr(m, "inc") else None


def test_counter_cached_by_name() -> None:
    a = counter("test_counter_cached_total", "description")
    b = counter("test_counter_cached_total", "description")
    assert a is b


def test_histogram_returns_a_metric_or_noop() -> None:
    m = histogram("test_hist_seconds", "description")
    m.observe(0.1) if hasattr(m, "observe") else None


def test_render_text_always_returns_bytes() -> None:
    text = render_text()
    assert isinstance(text, bytes)


def test_get_registry_is_stable() -> None:
    reg1 = get_registry()
    reg2 = get_registry()
    # Both either None (no prometheus) or the same object.
    assert reg1 is reg2


def test_noop_metric_label_chain() -> None:
    """Labels then inc should not raise on the noop."""
    # If prometheus_client is missing, the counter() helper returns
    # the noop; call labels + inc to exercise it.
    m = counter("noop_smoke_total", "d")
    m.labels(a="1").inc()
