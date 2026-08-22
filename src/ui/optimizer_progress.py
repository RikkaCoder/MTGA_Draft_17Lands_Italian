"""Determinate, localized optimizer progress presentation for Tkinter panels."""

from __future__ import annotations

import time
from tkinter import ttk

from src.i18n import format_number, tr, translate_generated
from src.ui.styles import Theme


PHASE_KEYS = {
    "preparing": "optimizer.preparing",
    "deck_variants": "optimizer.analyzing_variants",
    "variant_simulation": "optimizer.variant_simulation",
    "mana_optimization": "optimizer.optimizing_mana",
    "mana_simulation": "optimizer.mana_simulation",
    "monte_carlo": "optimizer.final_simulation",
    "final_simulation": "optimizer.final_simulation",
    "cache": "optimizer.cache",
    "completed": "optimizer.completed",
    "cancelled": "optimizer.cancelled",
    "error": "optimizer.error",
}


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


class OptimizerProgressView:
    """A small progress dashboard; all public methods must run on Tk's thread."""

    def __init__(self, owner, frame):
        self.owner = owner
        self.frame = frame
        self.started_at = time.monotonic()
        self.phase_started_at = self.started_at
        self.last_update_at = self.started_at
        self.last_phase = "preparing"
        self.last_event = {}
        self._heartbeat_id = None
        self._build()
        self._schedule_heartbeat()

    def _build(self):
        for widget in self.frame.winfo_children():
            widget.destroy()

        ttk.Label(
            self.frame,
            text=tr("optimizer.title"),
            font=Theme.scaled_font(12, "bold"),
            bootstyle="primary",
        ).pack(pady=Theme.scaled_val((12, 6)))

        self.phase_label = ttk.Label(
            self.frame,
            text=tr("optimizer.preparing"),
            font=Theme.scaled_font(10, "bold"),
            justify="center",
        )
        self.phase_label.pack(pady=Theme.scaled_val(3))

        self.detail_label = ttk.Label(
            self.frame,
            text="",
            justify="center",
            wraplength=Theme.scaled_val(320),
        )
        self.detail_label.pack(pady=Theme.scaled_val(2))

        self.progress = ttk.Progressbar(
            self.frame,
            mode="determinate",
            maximum=100,
            length=Theme.scaled_val(300),
        )
        self.progress.pack(fill="x", padx=Theme.scaled_val(20), pady=Theme.scaled_val(4))

        self.count_label = ttk.Label(self.frame, text=tr("optimizer.starting"))
        self.count_label.pack(pady=Theme.scaled_val(2))

        self.overall_label = ttk.Label(self.frame, text="")
        self.overall_progress = ttk.Progressbar(
            self.frame,
            mode="determinate",
            maximum=100,
            length=Theme.scaled_val(300),
        )

        self.elapsed_label = ttk.Label(self.frame, text="")
        self.elapsed_label.pack(pady=Theme.scaled_val((8, 1)))
        self.eta_label = ttk.Label(self.frame, text="")
        self.eta_label.pack(pady=Theme.scaled_val(1))
        self.activity_label = ttk.Label(
            self.frame,
            text=tr("optimizer.active"),
            bootstyle="success",
            justify="center",
            wraplength=Theme.scaled_val(320),
        )
        self.activity_label.pack(pady=Theme.scaled_val((5, 12)))
        self._refresh_clock()

    def update(self, event):
        self.last_event = dict(event)
        self.last_update_at = time.monotonic()
        phase = event.get("phase", "preparing")
        if phase != self.last_phase:
            self.phase_started_at = self.last_update_at
            self.last_phase = phase

        if phase == "error":
            self.fail()
            return

        phase_key = PHASE_KEYS.get(phase, event.get("message_key", "optimizer.preparing"))
        phase_args = {}
        if phase == "variant_simulation":
            phase_args = {
                "current": event.get("variant_current", 0),
                "total": event.get("variant_total", 0),
            }
        self.phase_label.config(text=tr(phase_key, **phase_args))

        detail = event.get("detail")
        if detail:
            detail_text = translate_generated(str(detail))
            if phase in ("deck_variants", "variant_simulation"):
                detail_text = tr("optimizer.current_variant", name=detail_text)
            elif phase in ("mana_optimization", "mana_simulation"):
                configuration_current = event.get("configuration_current")
                configuration_total = event.get("configuration_total")
                if configuration_current and configuration_total:
                    detail_text = tr(
                        "optimizer.current_configuration",
                        current=configuration_current,
                        total=configuration_total,
                        detail=detail_text,
                    )
            elif phase == "completed":
                detail_text = tr("optimizer.selected_configuration", name=detail_text)
            self.detail_label.config(text=detail_text)
        else:
            self.detail_label.config(text="")

        current = int(event.get("current") or 0)
        total = event.get("total")
        total = int(total) if total is not None else 0
        percent = min(100.0, (current / total * 100.0) if total > 0 else 0.0)
        self.progress["value"] = percent
        if total > 0:
            self.count_label.config(
                text=tr(
                    "optimizer.progress_count",
                    current=format_number(current),
                    total=format_number(total),
                    percent=format_number(percent, 1),
                )
            )
        else:
            self.count_label.config(text=tr("optimizer.working"))

        overall_total = int(event.get("overall_total") or 0)
        overall_current = event.get("overall_current")
        if overall_current is None and "overall_offset" in event:
            overall_current = int(event["overall_offset"]) + current
        if overall_total > 0 and overall_current is not None:
            overall_percent = min(100.0, int(overall_current) / overall_total * 100.0)
            self.overall_label.config(
                text=tr(
                    "optimizer.overall_progress",
                    percent=format_number(overall_percent, 1),
                )
            )
            if not self.overall_label.winfo_manager():
                self.overall_label.pack(pady=Theme.scaled_val((7, 1)))
                self.overall_progress.pack(
                    fill="x", padx=Theme.scaled_val(20), pady=Theme.scaled_val(2)
                )
            self.overall_progress["value"] = overall_percent
        else:
            self.overall_label.pack_forget()
            self.overall_progress.pack_forget()

        phase_elapsed = self.last_update_at - self.phase_started_at
        if total > 0 and current > 0 and current < total and phase_elapsed >= 1.0:
            remaining = phase_elapsed * (total - current) / current
            self.eta_label.config(
                text=tr("optimizer.estimated_remaining", time=format_duration(remaining))
            )
        else:
            self.eta_label.config(text="")
        self._refresh_clock()

    def complete(self, detail=None):
        event = dict(self.last_event)
        event.update(
            {
                "phase": "completed",
                "current": event.get("total", event.get("current", 1)) or 1,
                "total": event.get("total", event.get("current", 1)) or 1,
            }
        )
        if detail:
            event["detail"] = detail
        self.update(event)
        self.progress["value"] = 100
        self.eta_label.config(text="")
        self.activity_label.config(
            text=tr("optimizer.total_time", time=format_duration(self.elapsed_seconds)),
            bootstyle="success",
        )
        self.stop()

    def fail(self):
        failed_phase = self.phase_label.cget("text")
        self.phase_label.config(text=tr("optimizer.error"))
        self.detail_label.config(
            text=tr("optimizer.failed_phase", phase=failed_phase)
        )
        self.activity_label.config(
            text=tr("optimizer.error_detail"),
            bootstyle="danger",
        )
        self.eta_label.config(text="")
        self.stop()

    def cancel(self, message_key="optimizer.cancelled"):
        self.phase_label.config(text=tr(message_key))
        self.detail_label.config(text="")
        self.eta_label.config(text="")
        self.activity_label.config(text=tr("optimizer.restarting"), bootstyle="warning")
        self.stop()

    @property
    def elapsed_seconds(self):
        return time.monotonic() - self.started_at

    def _refresh_clock(self):
        now = time.monotonic()
        self.elapsed_label.config(
            text=tr("optimizer.elapsed_time", time=format_duration(now - self.started_at))
        )
        age = now - self.last_update_at
        if age < 10:
            text = tr("optimizer.active_recent", seconds=format_number(age, 1))
            style = "success"
        elif age < 30:
            text = tr("optimizer.no_recent_updates")
            style = "warning"
        else:
            text = tr("optimizer.stale", seconds=int(age))
            style = "danger"
        self.activity_label.config(text=text, bootstyle=style)

    def _schedule_heartbeat(self):
        if not self.frame.winfo_exists():
            return
        self._refresh_clock()
        self._heartbeat_id = self.owner.after(500, self._schedule_heartbeat)

    def stop(self):
        if self._heartbeat_id is not None:
            try:
                self.owner.after_cancel(self._heartbeat_id)
            except Exception:
                pass
            self._heartbeat_id = None
