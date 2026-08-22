"""Lightweight, optional progress events for optimizer workloads."""

from __future__ import annotations

import logging
from typing import Any, Callable, Mapping


logger = logging.getLogger(__name__)

ProgressCallback = Callable[[dict[str, Any]], None]


def emit_progress(
    callback: ProgressCallback | None,
    phase: str,
    current: int = 0,
    total: int | None = None,
    *,
    detail: str | None = None,
    message_key: str | None = None,
    context: Mapping[str, Any] | None = None,
) -> None:
    """Emit a structured event without letting presentation failures affect results."""
    if callback is None:
        return

    event: dict[str, Any] = {
        "phase": phase,
        "current": current,
        "total": total,
        "message_key": message_key or f"optimizer.{phase}",
    }
    if detail is not None:
        event["detail"] = detail
    if context:
        event.update(context)

    try:
        callback(event)
    except Exception:
        logger.exception("[Optimizer] Progress callback failed during %s", phase)
