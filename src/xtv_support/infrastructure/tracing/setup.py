"""OpenTelemetry bootstrap.

Wired from ``__main__.py`` when ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set.
All imports are lazy so the observability extra stays optional.
"""
from __future__ import annotations

import os

from xtv_support.core.logger import get_logger

_log = get_logger("otel.setup")

_installed = False


def install() -> bool:
    """Configure the global tracer provider. Returns True on success."""
    global _installed
    if _installed:
        return True

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        _log.debug("otel.install.skipped_no_endpoint")
        return False

    try:
        from opentelemetry import trace  # type: ignore[import-not-found]
        from opentelemetry.sdk.resources import Resource  # type: ignore[import-not-found]
        from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import-not-found]
        from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        _log.warning("otel.install.missing_packages", error=str(exc))
        return False

    exporter = _build_exporter()
    if exporter is None:
        return False

    resource = Resource.create(
        {
            "service.name": os.environ.get("OTEL_SERVICE_NAME", "xtv-support"),
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _installed = True
    _log.info(
        "otel.install.ok",
        endpoint=endpoint,
        service=os.environ.get("OTEL_SERVICE_NAME", "xtv-support"),
    )
    return True


def _build_exporter():
    protocol = os.environ.get("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc").lower()
    try:
        if protocol == "http/protobuf" or protocol == "http":
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore[import-not-found]
                OTLPSpanExporter,
            )
        else:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore[import-not-found]
                OTLPSpanExporter,
            )
    except ModuleNotFoundError as exc:
        _log.warning("otel.exporter.missing", protocol=protocol, error=str(exc))
        return None
    return OTLPSpanExporter()
