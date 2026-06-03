"""
MedLearn AI - Telemetry (OpenTelemetry tracing)

Adds distributed tracing across the orchestrator and the 6 agents so the
multi-step reasoning pipeline is observable: one span per agent call, plus
the Critic review/regeneration loop and escalation routing, with useful
attributes (agent name, confidence, verdict, quality score, regeneration
count).

Design principles:
    - ADDITIVE & SAFE. If OpenTelemetry isn't installed, or telemetry is
      disabled, every helper degrades to a no-op. Agent/orchestrator code
      never breaks because of telemetry.
    - CONSOLE BY DEFAULT. With ENABLE_TELEMETRY=true and no Azure connection
      string, spans print to the console — zero external dependencies, always
      works, great for the demo ("watch the reasoning pipeline trace itself").
    - AZURE MONITOR (optional). If APPLICATIONINSIGHTS_CONNECTION_STRING is
      set, spans also export to Azure Monitor / Application Insights for the
      production-observability story.

Environment variables:
    ENABLE_TELEMETRY                       "true" to turn tracing on (default off)
    APPLICATIONINSIGHTS_CONNECTION_STRING  optional; enables Azure Monitor export

Usage:
    from medlearn.telemetry import setup_telemetry, span

    setup_telemetry()  # once, at process start (orchestrator / UI / test)

    with span("agent.curator", {"learner_id": "CLN-N-001"}) as s:
        result = curator.recommend(...)
        if s:  # span may be None when telemetry is off
            s.set_attribute("medlearn.confidence", result.confidence)
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional

# ---------------------------------------------------------------------------
# Soft imports — telemetry must never hard-crash the app if OTel is absent.
# ---------------------------------------------------------------------------
try:
    from opentelemetry import trace as _otel_trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )

    _OTEL_AVAILABLE = True
except Exception:  # pragma: no cover - import guard
    _OTEL_AVAILABLE = False


_INITIALIZED = False
_TELEMETRY_ON = False
_SERVICE_NAME = "medlearn-ai"


def _telemetry_requested() -> bool:
    return os.getenv("ENABLE_TELEMETRY", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def setup_telemetry(force: bool = False) -> bool:
    """Initialize the global tracer provider exactly once.

    Returns True if telemetry is active afterwards, False otherwise.

    - No-op (returns False) if OTel isn't installed or ENABLE_TELEMETRY is off
      (unless force=True).
    - Always wires a console exporter so traces are visible locally.
    - Additionally wires Azure Monitor if a connection string is present.
    """
    global _INITIALIZED, _TELEMETRY_ON

    if _INITIALIZED:
        return _TELEMETRY_ON

    if not _OTEL_AVAILABLE:
        _INITIALIZED = True
        _TELEMETRY_ON = False
        return False

    if not (_telemetry_requested() or force):
        _INITIALIZED = True
        _TELEMETRY_ON = False
        return False

    resource = Resource.create({"service.name": _SERVICE_NAME})
    provider = TracerProvider(resource=resource)

    # Console exporter — always on when telemetry is enabled. Zero deps.
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    # Optional Azure Monitor export (the "production observability" story).
    conn = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if conn:
        try:
            from azure.monitor.opentelemetry.exporter import (
                AzureMonitorTraceExporter,
            )

            provider.add_span_processor(
                BatchSpanProcessor(
                    AzureMonitorTraceExporter(connection_string=conn)
                )
            )
        except Exception:
            # Azure exporter not installed or misconfigured — keep console only.
            pass

    _otel_trace.set_tracer_provider(provider)
    _INITIALIZED = True
    _TELEMETRY_ON = True
    return True


def is_on() -> bool:
    """True if telemetry is initialized and active."""
    return _TELEMETRY_ON


@contextmanager
def span(name: str, attributes: Optional[Dict[str, Any]] = None) -> Iterator[Any]:
    """Context manager yielding an active span (or None when telemetry is off).

    Safe to use unconditionally:

        with span("agent.curator", {"learner_id": lid}) as s:
            ...
            if s:
                s.set_attribute("medlearn.confidence", conf)
    """
    if not _TELEMETRY_ON or not _OTEL_AVAILABLE:
        yield None
        return

    tracer = _otel_trace.get_tracer(_SERVICE_NAME)
    with tracer.start_as_current_span(name) as current:
        if attributes:
            for key, value in attributes.items():
                if value is not None:
                    current.set_attribute(key, value)
        yield current


def set_attributes(s: Any, attributes: Dict[str, Any]) -> None:
    """Safely set multiple attributes on a span that may be None."""
    if s is None:
        return
    for key, value in attributes.items():
        if value is not None:
            try:
                s.set_attribute(key, value)
            except Exception:
                pass


def traced(span_name: str):
    """Decorator that wraps a method call in a span.

    Safe when telemetry is off (runs the method directly, no overhead beyond
    a boolean check). After the wrapped method returns, common MedLearn
    result attributes are auto-extracted onto the span if present
    (confidence, verdict, overall_quality_score, action, readiness_level).

        @traced("agent.curator.recommend")
        def recommend(self, ...): ...
    """

    # Result fields worth surfacing as span attributes when they exist.
    _AUTO_ATTRS = (
        "confidence",
        "verdict",
        "overall_quality_score",
        "action",
        "readiness_level",
        "target_certification_id",
        "overall_health_status",
        "pipeline_status",
        "total_critic_regenerations",
        "escalation_triggered",
    )

    def decorator(func):
        import functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not _TELEMETRY_ON or not _OTEL_AVAILABLE:
                return func(*args, **kwargs)
            with span(span_name) as s:
                result = func(*args, **kwargs)
                if s is not None and result is not None:
                    for attr in _AUTO_ATTRS:
                        val = getattr(result, attr, None)
                        if val is not None and isinstance(
                            val, (str, int, float, bool)
                        ):
                            try:
                                s.set_attribute(f"medlearn.{attr}", val)
                            except Exception:
                                pass
                return result

        return wrapper

    return decorator
