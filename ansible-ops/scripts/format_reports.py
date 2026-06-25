#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


STATUS_ORDER = {
    "critical": 0,
    "failed": 1,
    "warning": 2,
    "skipped": 3,
    "ok": 4,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Format Ansible JSON artifacts into a readable Markdown report.")
    parser.add_argument("--artifact-dir", default="artifacts", help="Directory that contains os/ and k8s/ artifacts.")
    parser.add_argument("--output", default="artifacts/report.md", help="Markdown report output path.")
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir)
    reports = load_reports(artifact_dir)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(reports), encoding="utf-8")
    print(f"Wrote report: {output}")
    return 0


def load_reports(artifact_dir: Path) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for path in sorted(artifact_dir.glob("*/*/*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            reports.append(
                {
                    "job": path.stem,
                    "name": "Invalid report file",
                    "host": path.parent.name,
                    "status": "failed",
                    "message": f"Cannot read {path}: {exc}",
                    "summary": {},
                    "highlights": {},
                }
            )
            continue

        if isinstance(data, dict):
            data["_source"] = str(path)
            reports.append(data)

    return sorted(
        reports,
        key=lambda item: (
            item.get("host", ""),
            STATUS_ORDER.get(str(item.get("status", "")).lower(), 99),
            item.get("job", ""),
        ),
    )


def render_markdown(reports: list[dict[str, Any]]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Ansible Automation Report",
        "",
        f"- Generated: {now}",
        f"- Total jobs: {len(reports)}",
        "",
    ]

    lines.extend(render_overview(reports))

    current_host = None
    for report in reports:
        host = str(report.get("host") or "unknown")
        if host != current_host:
            current_host = host
            lines.extend(["", f"## Host: {host}", ""])

        status = str(report.get("status") or "unknown").upper()
        job = str(report.get("job") or "UNKNOWN-JOB")
        name = str(report.get("name") or "")
        title = f"{job} - {name}" if name else job
        lines.extend([f"### [{status}] {title}", ""])

        message = report.get("message")
        if message:
            lines.extend([f"**Message:** {one_line(message)}", ""])

        lines.extend(render_mapping("Summary", report.get("summary")))
        lines.extend(render_mapping("Highlights", report.get("highlights"), max_items=12))

    return "\n".join(lines).rstrip() + "\n"


def render_overview(reports: list[dict[str, Any]]) -> list[str]:
    counts: dict[str, int] = {}
    for report in reports:
        status = str(report.get("status") or "unknown").lower()
        counts[status] = counts.get(status, 0) + 1

    lines = ["## Overview", ""]
    for status in ["critical", "failed", "warning", "skipped", "ok", "unknown"]:
        if status in counts:
            lines.append(f"- {status.upper()}: {counts[status]}")
    lines.append("")
    return lines


def render_mapping(title: str, value: Any, max_items: int | None = None) -> list[str]:
    if not isinstance(value, dict) or not value:
        return []

    lines = [f"**{title}:**", ""]
    printed = 0
    for key, item in value.items():
        if is_empty(item):
            continue
        if max_items is not None and printed >= max_items:
            lines.append("- ...")
            break
        lines.append(f"- `{key}`: {format_value(item)}")
        printed += 1
    lines.append("")
    return lines if printed else []


def format_value(value: Any) -> str:
    if isinstance(value, dict):
        compact = json.dumps(value, ensure_ascii=False, sort_keys=True)
        return trim(compact)
    if isinstance(value, list):
        if not value:
            return "none"
        items = [format_value(item) for item in value[:6]]
        suffix = "" if len(value) <= 6 else f" ... (+{len(value) - 6} more)"
        return "; ".join(items) + suffix
    return trim(one_line(value))


def one_line(value: Any) -> str:
    return " ".join(str(value).split())


def trim(value: str, limit: int = 300) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


if __name__ == "__main__":
    raise SystemExit(main())
