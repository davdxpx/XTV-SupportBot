"""Prometheus metrics registry.

Lazy-imports ``prometheus_client`` so the module stays importable
without the ``observability`` extra installed. The registry + metric
objects are singletons per-process; the FastAPI route in
``api/routes/system.py`` serves them in OpenMetrics format.
"""

from __future__ import annotations

from typing import Any

_registry: Any = None
_counters: dict[str, Any] = {}
_histograms: dict[str, Any] = {}


def _prom_available() -> bool:
    try:
        import prometheus_client  # type: ignore[import-untyped]  # noqa: F401

        return True
    except ModuleNotFoundError:
        return False


def get_registry() -> Any:
    """Return the shared CollectorRegistry, creating it on first call."""
    global _registry
    if _registry is not None:
        return _registry
    if not _prom_available():
        return None
    import prometheus_client  # type: ignore[import-untyped]

    _registry = prometheus_client.CollectorRegistry(auto_describe=True)
    return _registry


def counter(name: str, description: str, labels: list[str] | None = None) -> Any:
    if name in _counters:
        return _counters[name]
    if not _prom_available():
        metric: Any = _NoopMetric()
    else:
        import prometheus_client  # type: ignore[import-untyped]

        metric = prometheus_client.Counter(
            name, description, labelnames=list(labels or ()), registry=get_registry()
        )
    _counters[name] = metric
    return metric


def histogram(name: str, description: str, labels: list[str] | None = None) -> Any:
    if name in _histograms:
        return _histograms[name]
    if not _prom_available():
        metric: Any = _NoopMetric()
    else:
        import prometheus_client  # type: ignore[import-untyped]

        metric = prometheus_client.Histogram(
            name, description, labelnames=list(labels or ()), registry=get_registry()
        )
    _histograms[name] = metric
    return metric


def render_text() -> bytes:
    """Return the current metrics in Prometheus text format."""
    if not _prom_available() or _registry is None:
        return b""
    import prometheus_client  # type: ignore[import-untyped]

    return prometheus_client.generate_latest(_registry)


class _NoopMetric:
    """Silently-accepts-everything metric used when prometheus_client is absent."""

    def labels(self, **_kw):
        return self

    def inc(self, *_a, **_k):
        pass

    def observe(self, *_a, **_k):
        pass
