# Copyright: local project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from ansible.plugins.callback import CallbackBase


DOCUMENTATION = r"""
callback: readable_output
type: stdout
short_description: Human friendly output for check reports
description:
  - Prints Ansible check reports in a compact, readable format.
  - Keeps task noise low and expands only structured C(*_job_*_report) values.
"""


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "stdout"
    CALLBACK_NAME = "readable_output"

    STATUS_COLORS = {
        "ok": "green",
        "warning": "yellow",
        "critical": "red",
        "failed": "red",
        "skipped": "blue",
    }

    def __init__(self) -> None:
        super().__init__()
        self._play_failed_hosts = set()
        self._play_skipped_hosts = set()

    def v2_playbook_on_start(self, playbook) -> None:
        self._display.banner("ANSIBLE CHECKS")
        self._display.display(f"Playbook: {playbook._file_name}")

    def v2_playbook_on_play_start(self, play) -> None:
        self._display.banner(play.get_name().strip() or "Play")

    def v2_runner_on_ok(self, result) -> None:
        report = self._extract_report(result._result)
        if report:
            self._print_report(result._host.get_name(), report)
            return

        if not result._result.get("changed", False):
            return

        task_name = self._task_name(result)
        self._display.display(f"CHANGED: {result._host.get_name()} | {task_name}", color="yellow")

    def v2_runner_on_failed(self, result, ignore_errors=False) -> None:
        host = result._host.get_name()
        self._play_failed_hosts.add(host)
        task_name = self._task_name(result) or "task"
        self._display.display(f"FAILED: {host} | {task_name}", color="red")
        self._print_failure_detail(result._result)
        if ignore_errors:
            self._display.display("  ignored: true", color="yellow")

    def v2_runner_on_skipped(self, result) -> None:
        host = result._host.get_name()
        self._play_skipped_hosts.add(host)
        task_name = self._task_name(result) or "task"
        self._display.display(f"SKIPPED: {host} | {task_name}", color="blue")

    def v2_playbook_on_stats(self, stats) -> None:
        self._display.banner("SUMMARY")
        hosts = sorted(stats.processed.keys())
        for host in hosts:
            summary = stats.summarize(host)
            status = self._host_status(host, summary)
            color = self.STATUS_COLORS.get(status, "normal")
            parts = [
                f"ok={summary.get('ok', 0)}",
                f"changed={summary.get('changed', 0)}",
                f"failed={summary.get('failures', 0)}",
                f"skipped={summary.get('skipped', 0)}",
                f"unreachable={summary.get('unreachable', 0)}",
            ]
            self._display.display(f"{status.upper():8} {host}: " + ", ".join(parts), color=color)

    def _extract_report(self, payload):
        if not isinstance(payload, Mapping):
            return None

        for value in payload.values():
            if self._looks_like_report(value):
                return value

        ansible_facts = payload.get("ansible_facts")
        if isinstance(ansible_facts, Mapping):
            for value in ansible_facts.values():
                if self._looks_like_report(value):
                    return value

        return None

    def _looks_like_report(self, value) -> bool:
        return (
            isinstance(value, Mapping)
            and "job" in value
            and "status" in value
            and "summary" in value
        )

    def _print_report(self, host, report) -> None:
        job = self._stringify(report.get("job", "REPORT"))
        name = self._stringify(report.get("name", ""))
        status = self._stringify(report.get("status", "ok")).lower()
        message = self._stringify(report.get("message", ""))
        color = self.STATUS_COLORS.get(status, "normal")

        title = f"{job} | {name}" if name else job
        self._display.display("")
        self._display.display(f"{title}", color="cyan")
        self._display.display(f"  Host   : {report.get('host') or host}")
        self._display.display(f"  Status : {status.upper()}", color=color)
        if message:
            self._display.display(f"  Message: {message}", color=color)

        self._print_mapping("Summary", report.get("summary"))
        self._print_mapping("Highlights", report.get("highlights"), max_items=10)

    def _print_mapping(self, title, value, max_items=None) -> None:
        if not isinstance(value, Mapping) or not value:
            return

        self._display.display(f"  {title}:")
        for index, (key, item) in enumerate(value.items()):
            if max_items is not None and index >= max_items:
                self._display.display("    ...")
                break
            if self._is_empty(item):
                continue
            self._display.display(f"    - {key}: {self._format_value(item)}")

    def _print_sequence(self, title, value, max_items=None) -> None:
        if self._is_empty(value):
            return

        if isinstance(value, str):
            value = [value]
        if not isinstance(value, Sequence):
            value = [value]

        self._display.display(f"  {title}:")
        for index, item in enumerate(value):
            if max_items is not None and index >= max_items:
                self._display.display("    ...")
                break
            self._display.display(f"    - {self._format_value(item)}")

    def _format_value(self, value):
        if isinstance(value, Mapping):
            compact = json.dumps(value, ensure_ascii=False, sort_keys=True)
            return self._trim(compact)
        if isinstance(value, Sequence) and not isinstance(value, str):
            if not value:
                return "none"
            lines = [self._format_value(item) for item in list(value)[:5]]
            suffix = "" if len(value) <= 5 else f" ... (+{len(value) - 5} more)"
            return "; ".join(lines) + suffix
        return self._trim(self._stringify(value))

    def _host_status(self, host, summary):
        if summary.get("unreachable", 0) or summary.get("failures", 0):
            return "failed"
        if host in self._play_skipped_hosts and summary.get("ok", 0) == 0:
            return "skipped"
        return "ok"

    def _task_name(self, result) -> str:
        task_name = getattr(result, "task_name", None)
        if task_name:
            return task_name
        task = getattr(result, "_task", None)
        if task is not None:
            return task.get_name().strip()
        return ""

    def _print_failure_detail(self, payload) -> None:
        cmd = payload.get("cmd")
        rc = payload.get("rc")
        msg = payload.get("msg")
        stderr = payload.get("stderr")

        if cmd:
            self._display.display(f"  cmd: {self._format_value(cmd)}", color="red")
        if rc is not None:
            self._display.display(f"  rc : {rc}", color="red")
        if msg:
            self._display.display(f"  msg: {self._stringify(msg)}", color="red")
        if stderr:
            self._display.display(f"  err: {self._stringify(stderr)}", color="red")

    def _is_empty(self, value) -> bool:
        return value is None or value == "" or value == [] or value == {}

    def _stringify(self, value) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    def _trim(self, value, limit=220) -> str:
        if len(value) <= limit:
            return value
        return value[: limit - 3] + "..."
