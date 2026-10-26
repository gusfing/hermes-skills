#!/usr/bin/env python3
"""
Todoist Task Review Analyzer

Analyzes a JSON list of Todoist tasks and produces actionable suggestions
for improving productivity and task hygiene.

Usage:
    python todoist_review.py <tasks.json>
    python todoist_review.py <tasks.json> --output report.txt

Input format (JSON array of task objects):
    [
        {
            "content": "Submit expense report",
            "priority": 3,
            "due": {"date": "2026-08-15", "is_recurring": false},
            "project_id": "12345",
            "labels": ["@office", "@5min"],
            "created_at": "2026-07-01T10:00:00Z",
            "is_completed": false
        },
        ...
    ]

The script outputs a structured report with sections:
    - Summary statistics
    - Overdue tasks review
    - Priority distribution analysis
    - Missing due dates on high-priority tasks
    - Stale tasks detection
    - Label usage audit
    - Actionable recommendations
"""

import json
import sys
import os
import argparse
from datetime import datetime, timezone
from collections import Counter
from typing import Any


def load_tasks(filepath: str) -> list[dict[str, Any]]:
    """Load tasks from a JSON file. Returns a list of task dicts."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of task objects.")
    return data


def parse_date(date_str: str | None) -> datetime | None:
    """Parse an ISO date string into a timezone-aware UTC datetime. Returns None on failure."""
    if not date_str:
        return None
    try:
        # Handle dates like "2026-08-15" or "2026-08-15T10:00:00Z"
        normalized = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        # If the parsed datetime is naive (e.g., "2026-08-15" has no timezone),
        # assume UTC for consistent comparisons.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def days_ago(dt: datetime, now: datetime) -> int:
    """Return the number of whole days between dt and now."""
    return (now - dt).days


def analyze(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Analyze a list of tasks and return a dict with findings and recommendations.
    """
    now = datetime.now(timezone.utc)
    findings: dict[str, Any] = {
        "total": 0,
        "completed": 0,
        "active": 0,
        "overdue": [],
        "high_priority_no_due": [],
        "priority_counts": Counter(),
        "no_project": [],
        "stale": [],
        "label_usage": Counter(),
        "label_suggestions": [],
        "recurring_count": 0,
        "recommendations": [],
    }

    active_tasks = [t for t in tasks if not t.get("is_completed", False)]
    completed_tasks = [t for t in tasks if t.get("is_completed", False)]

    findings["total"] = len(tasks)
    findings["completed"] = len(completed_tasks)
    findings["active"] = len(active_tasks)

    for task in active_tasks:
        priority = task.get("priority", 3)
        findings["priority_counts"][priority] += 1

        # Overdue detection
        due = task.get("due")
        if due and not due.get("is_recurring", False) and due.get("date"):
            due_date = parse_date(due["date"])
            if due_date and due_date < now:
                findings["overdue"].append({
                    "content": task.get("content", "(untitled)"),
                    "priority": priority,
                    "due": due["date"],
                    "days_overdue": days_ago(due_date, now),
                })

        # Recurring tasks
        if due and due.get("is_recurring", False):
            findings["recurring_count"] += 1

        # High priority (p1 or p2) without due date
        if priority in (1, 2) and (not due or not due.get("date")):
            findings["high_priority_no_due"].append({
                "content": task.get("content", "(untitled)"),
                "priority": priority,
            })

        # Tasks without a project
        if not task.get("project_id"):
            findings["no_project"].append({
                "content": task.get("content", "(untitled)"),
                "priority": priority,
            })

        # Stale tasks: no due date and created more than 14 days ago
        created_at = task.get("created_at")
        if not due or not due.get("date"):
            created_dt = parse_date(created_at)
            if created_dt and days_ago(created_dt, now) > 14:
                findings["stale"].append({
                    "content": task.get("content", "(untitled)"),
                    "priority": priority,
                    "created_at": created_at,
                    "days_since_creation": days_ago(created_dt, now),
                })

        # Label usage
        labels = task.get("labels", [])
        for label in labels:
            findings["label_usage"][label] += 1

    # --- Generate Recommendations ---

    # Overdue tasks
    if findings["overdue"]:
        findings["recommendations"].append(
            f"Overdue tasks ({len(findings['overdue'])}): Resolve each one by completing, "
            "rescheduling, or canceling. An overdue list longer than 5 items erodes trust "
            "in your system."
        )

    # P1 overload
    p1_count = findings["priority_counts"].get(1, 0)
    if p1_count > 5:
        findings["recommendations"].append(
            f"P1 overload ({p1_count} tasks): You have more than 5 p1 tasks. "
            "Re-evaluate: true p1 tasks should be capped at ~3 per day. "
            "Downgrade less critical items to p2 or p3."
        )

    # High priority without due dates
    if findings["high_priority_no_due"]:
        findings["recommendations"].append(
            f"High-priority tasks without due dates ({len(findings['high_priority_no_due'])}): "
            "p1 and p2 tasks should have deadlines. Add due dates to anchor them in time "
            "and prevent them from lingering indefinitely."
        )

    # No project tasks
    no_project_count = len(findings["no_project"])
    if no_project_count > 0:
        findings["recommendations"].append(
            f"Orphan tasks ({no_project_count}): Tasks without a project live in "
            "your Inbox. Process them: assign a project, or move to Someday/Maybe "
            "if not yet actionable."
        )

    # Stale tasks
    if findings["stale"]:
        findings["recommendations"].append(
            f"Stale tasks ({len(findings['stale'])}): Tasks older than 14 days with no due "
            "date and no labels. These need a decision — schedule them, label them "
            "@someday, or delete them."
        )

    # Label audit
    distinct_labels = len(findings["label_usage"])
    if distinct_labels > 20:
        findings["label_suggestions"].append(
            f"You have {distinct_labels} distinct labels. Consider pruning to 15-20 "
            "to reduce decision fatigue. Review rarely-used labels."
        )
    if distinct_labels == 0 and findings["active"] > 5:
        findings["label_suggestions"].append(
            "No labels in use. Labels add context (energy, location, time) that "
            "enables powerful filtering. Consider adding @computer, @phone, @deep_work, "
            "@shallow, @5min, @15min, @30min labels."
        )

    # Completion ratio
    if findings["total"] > 10:
        completion_pct = (findings["completed"] / findings["total"]) * 100
        if completion_pct < 10:
            findings["recommendations"].append(
                f"Low completion rate ({completion_pct:.0f}%): Only {findings['completed']} "
                f"of {findings['total']} tasks are completed. Review whether your tasks are "
                "too large, too vague, or whether you are over-committing."
            )

    # Priority distribution
    if findings["active"] > 0:
        pct_p1 = (p1_count / findings["active"]) * 100
        if pct_p1 > 30:
            findings["recommendations"].append(
                f"P1 tasks are {pct_p1:.0f}% of active tasks. Best practice is under 10%. "
                "Audit your p1 list — most tasks should be p2 or p3."
            )

    return findings


def format_report(findings: dict[str, Any]) -> str:
    """Format the analysis findings into a readable text report."""
    lines: list[str] = []

    lines.append("=" * 60)
    lines.append("TODOIST TASK REVIEW REPORT")
    lines.append("=" * 60)
    lines.append("")

    # Summary
    lines.append("--- SUMMARY ---")
    lines.append(f"Total tasks:      {findings['total']}")
    lines.append(f"Active:           {findings['active']}")
    lines.append(f"Completed:        {findings['completed']}")
    lines.append(f"Recurring:        {findings['recurring_count']}")
    lines.append("")

    # Priority distribution
    lines.append("--- PRIORITY DISTRIBUTION ---")
    for p in sorted(findings["priority_counts"].keys()):
        count = findings["priority_counts"][p]
        label = {1: "p1 (urgent)", 2: "p2 (high)", 3: "p3 (medium)", 4: "p4 (low)"}.get(p, f"p{p}")
        bar = "#" * min(count, 40)
        lines.append(f"  {label:20s} {count:4d}  {bar}")
    lines.append("")

    # Overdue
    lines.append(f"--- OVERDUE TASKS ({len(findings['overdue'])}) ---")
    if findings["overdue"]:
        for t in sorted(findings["overdue"], key=lambda x: x["days_overdue"], reverse=True):
            p_label = f"p{t['priority']}"
            lines.append(
                f"  [{p_label}] {t['content']}")
            lines.append(f"          Due: {t['due']} ({t['days_overdue']} days overdue)")
    else:
        lines.append("  No overdue tasks. Well done.")
    lines.append("")

    # High priority no due date
    lines.append(f"--- HIGH PRIORITY WITHOUT DUE DATE ({len(findings['high_priority_no_due'])}) ---")
    if findings["high_priority_no_due"]:
        for t in findings["high_priority_no_due"]:
            lines.append(f"  [p{t['priority']}] {t['content']}")
    else:
        lines.append("  All high-priority tasks have due dates. Good.")
    lines.append("")

    # No project
    lines.append(f"--- TASKS WITHOUT PROJECT ({len(findings['no_project'])}) ---")
    if findings["no_project"]:
        for t in findings["no_project"]:
            lines.append(f"  [p{t['priority']}] {t['content']}")
    else:
        lines.append("  All active tasks belong to a project.")
    lines.append("")

    # Stale
    lines.append(f"--- STALE TASKS ({len(findings['stale'])}) ---")
    if findings["stale"]:
        for t in sorted(findings["stale"], key=lambda x: x["days_since_creation"], reverse=True):
            lines.append(
                f"  [p{t['priority']}] {t['content']} "
                f"(created {t['days_since_creation']} days ago)"
            )
    else:
        lines.append("  No stale tasks detected.")
    lines.append("")

    # Label usage
    lines.append(f"--- LABEL USAGE ({len(findings['label_usage'])} distinct) ---")
    if findings["label_usage"]:
        for label, count in findings["label_usage"].most_common(20):
            lines.append(f"  {label:25s} {count:4d} tasks")
        if len(findings["label_usage"]) > 20:
            lines.append(f"  ... and {len(findings['label_usage']) - 20} more labels")
    else:
        lines.append("  No labels in use.")
    if findings["label_suggestions"]:
        for s in findings["label_suggestions"]:
            lines.append(f"  SUGGESTION: {s}")
    lines.append("")

    # Recommendations
    lines.append(f"--- RECOMMENDATIONS ({len(findings['recommendations'])}) ---")
    if findings["recommendations"]:
        for i, rec in enumerate(findings["recommendations"], 1):
            lines.append(f"  {i}. {rec}")
    else:
        lines.append("  Your task list looks healthy. No major issues found.")
    lines.append("")

    lines.append("=" * 60)
    lines.append("Review complete. Act on recommendations during your next Weekly Review.")
    lines.append("=" * 60)

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze a Todoist task list and suggest productivity improvements.",
    )
    parser.add_argument(
        "input",
        help="Path to JSON file containing a list of Todoist task objects.",
    )
    parser.add_argument(
        "--output", "-o",
        help="Write report to a file instead of stdout.",
    )
    args = parser.parse_args()

    try:
        if os.path.isfile(args.input):
            tasks = load_tasks(args.input)
        else:
            # Aceita JSON inline
            data = json.loads(args.input)
            if not isinstance(data, list):
                raise ValueError("Expected a JSON array of task objects.")
            tasks = data
    except FileNotFoundError:
        print(f"ERROR: File not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {args.input}: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if not tasks:
        print("WARNING: The input file contains no tasks.", file=sys.stderr)
        sys.exit(0)

    findings = analyze(tasks)
    report = format_report(findings)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
