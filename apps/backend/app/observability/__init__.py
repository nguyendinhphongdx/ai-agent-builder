"""Observability — error reporting, request logging, health probes."""
from app.observability.sentry import init_sentry

__all__ = ["init_sentry"]
