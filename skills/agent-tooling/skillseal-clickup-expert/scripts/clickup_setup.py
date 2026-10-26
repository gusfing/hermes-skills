#!/usr/bin/env python3
"""
clickup_setup.py — Validate a ClickUp workspace structure from a JSON file.

Accepts a JSON file path as a CLI argument. The JSON must describe a ClickUp
workspace hierarchy: Workspace -> Spaces -> Folders -> Lists -> Tasks.

Outputs validation results, counts, and actionable best-practice recommendations.

Usage:
    python3 clickup_setup.py workspace.json
    python3 clickup_setup.py --help
"""

import json
import sys
import os
from argparse import ArgumentParser, FileType
from collections import Counter
from typing import Any

# ---------------------------------------------------------------------------
# Expected JSON schema (informal)
# ---------------------------------------------------------------------------
# {
#   "workspace": {
#     "name": "Acme Corp",
#     "spaces": [
#       {
#         "name": "Marketing",
#         "folders": [
#           {
#             "name": "Q4 Campaign",
#             "lists": [
#               {
#                 "name": "Email Sequences",
#                 "statuses": ["To Do", "In Progress", "Done"],
#                 "tasks": [
#                   {
#                     "name": "Draft welcome email",
#                     "status": "In Progress",
#                     "assignee": "alice",
#                     "has_subtasks": false,
#                     "custom_fields": {}
#                   }
#                 ]
#               }
#             ]
#           }
#         ]
#       }
#     ]
#   }
# }
#
# Top-level spaces (without a folder) are also supported:
#   "spaces": [ { "name": "...", "lists": [ ... ] } ]
# Lists inside spaces (no folders) are also valid.
# ---------------------------------------------------------------------------

MAX_SPACES_WARN = 12
MAX_STATUSES_WARN = 10
MAX_FOLDERS_WARN = 20

ISSUES = []
WARNINGS = []
TIPS = []


def issue(msg: str) -> None:
    ISSUES.append(msg)


def warn(msg: str) -> None:
    WARNINGS.append(msg)


def tip(msg: str) -> None:
    TIPS.append(msg)


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def validate_workspace(ws: dict) -> dict:
    """Validate the top-level workspace object. Returns extracted metadata."""
    if not isinstance(ws, dict):
        issue("Workspace must be a JSON object.")
        return {}

    name = ws.get("name", "Unnamed Workspace")
    if not ws.get("name"):
        warn("Workspace has no 'name' field. Add a descriptive name.")

    spaces = ws.get("spaces", [])
    if not isinstance(spaces, list):
        issue("'spaces' must be an array.")
        return {"name": name, "space_count": 0}

    if len(spaces) == 0:
        issue("Workspace has zero Spaces. Create at least one Space to organize work.")
    elif len(spaces) > MAX_SPACES_WARN:
        tip(
            f"Workspace has {len(spaces)} Spaces (threshold: {MAX_SPACES_WARN}). "
            "Consider consolidating to fewer high-level Spaces for better navigation."
        )

    # Collect all statuses used across the workspace
    all_statuses: set[str] = set()
    total_folders = 0
    total_lists = 0
    total_tasks = 0
    tasks_with_subtasks = 0
    assignee_counts: Counter = Counter()
    space_without_folders = 0
    lists_without_tasks = 0
    status_counts: Counter = Counter()

    for sp in spaces:
        if not isinstance(sp, dict):
            issue(f"Space entry is not an object: {sp}")
            continue
        sp_name = sp.get("name", "Unnamed Space")
        if not sp.get("name"):
            warn("A Space has no 'name' field.")

        folders = sp.get("folders", [])
        direct_lists = sp.get("lists", [])

        if not isinstance(folders, list):
            issue(f"Space '{sp_name}': 'folders' must be an array.")
            folders = []
        if not isinstance(direct_lists, list):
            issue(f"Space '{sp_name}': 'lists' must be an array.")
            direct_lists = []

        has_folders = len(folders) > 0
        has_direct_lists = len(direct_lists) > 0

        if not has_folders and not has_direct_lists:
            warn(
                f"Space '{sp_name}' has no Folders and no direct Lists. "
                "Add at least one Folder or List to make the Space actionable."
            )

        # Validate folders
        for fld in folders:
            if not isinstance(fld, dict):
                issue(f"Space '{sp_name}': Folder entry is not an object.")
                continue
            fld_name = fld.get("name", "Unnamed Folder")
            total_folders += 1

            if not fld.get("name"):
                warn(f"Space '{sp_name}': A Folder has no 'name' field.")

            lists = fld.get("lists", [])
            if not isinstance(lists, list):
                issue(f"Space '{sp_name}' / Folder '{fld_name}': 'lists' must be an array.")
                continue

            if len(lists) == 0:
                warn(
                    f"Space '{sp_name}' / Folder '{fld_name}' has no Lists. "
                    "Add Lists to hold tasks."
                )

            for lst in lists:
                list_meta = validate_list(lst, context=f"Space '{sp_name}' / Folder '{fld_name}'")
                total_lists += 1
                total_tasks += list_meta["task_count"]
                tasks_with_subtasks += list_meta["subtask_count"]
                if list_meta["task_count"] == 0:
                    lists_without_tasks += 1
                all_statuses.update(list_meta["statuses_used"])
                status_counts.update(list_meta["statuses_used"])
                for a in list_meta["assignees"]:
                    assignee_counts[a] += 1

        # Validate direct lists on the space
        if has_direct_lists and has_folders:
            warn(
                f"Space '{sp_name}' has both Folders and direct Lists. "
                "This mixed layout can be confusing. Prefer one pattern: either "
                "use Folders to group Lists, or keep Lists directly in the Space."
            )

        for lst in direct_lists:
            list_meta = validate_list(lst, context=f"Space '{sp_name}' (direct)")
            total_lists += 1
            total_tasks += list_meta["task_count"]
            tasks_with_subtasks += list_meta["subtask_count"]
            if list_meta["task_count"] == 0:
                lists_without_tasks += 1
            all_statuses.update(list_meta["statuses_used"])
            status_counts.update(list_meta["statuses_used"])
            for a in list_meta["assignees"]:
                assignee_counts[a] += 1

    return {
        "name": name,
        "space_count": len(spaces),
        "folder_count": total_folders,
        "list_count": total_lists,
        "task_count": total_tasks,
        "tasks_with_subtasks": tasks_with_subtasks,
        "lists_without_tasks": lists_without_tasks,
        "all_statuses": all_statuses,
        "status_counts": status_counts,
        "assignee_counts": assignee_counts,
    }


def validate_list(lst: dict, context: str = "") -> dict:
    """Validate a single List and its tasks. Returns metadata dict."""
    name = lst.get("name", "Unnamed List")
    if not lst.get("name"):
        warn(f"{context}: A List has no 'name' field.")

    statuses = lst.get("statuses", [])
    if not isinstance(statuses, list):
        issue(f"{context} / List '{name}': 'statuses' must be an array.")
        statuses = []

    tasks = lst.get("tasks", [])
    if not isinstance(tasks, list):
        issue(f"{context} / List '{name}': 'tasks' must be an array.")
        tasks = []

    if len(statuses) > MAX_STATUSES_WARN:
        tip(
            f"{context} / List '{name}' has {len(statuses)} statuses "
            f"(threshold: {MAX_STATUSES_WARN}). "
            "Consider simplifying to 3-5 statuses and using a Custom Field "
            "dropdown for sub-stages."
        )

    statuses_used: set[str] = set()
    assigned: list[str] = []
    task_count = 0
    subtask_count = 0

    for t in tasks:
        if not isinstance(t, dict):
            issue(f"{context} / List '{name}': Task entry is not an object.")
            continue
        task_count += 1

        t_name = t.get("name", "")
        if not t_name:
            warn(f"{context} / List '{name}': A task has no 'name' field.")

        t_status = t.get("status", "")
        if t_status:
            if statuses and t_status not in statuses:
                warn(
                    f"{context} / List '{name}': Task '{t_name}' has status "
                    f"'{t_status}' which is not in the List's defined statuses: {statuses}"
                )
            statuses_used.add(t_status)

        assignee = t.get("assignee", "")
        if assignee:
            assigned.append(assignee)

        if t.get("has_subtasks", False):
            subtask_count += 1

    # Warn on unused statuses
    defined_not_used = set(statuses) - statuses_used
    if defined_not_used:
        warn(
            f"{context} / List '{name}': Statuses defined but never used by any task: "
            f"{sorted(defined_not_used)}. Remove unused statuses to keep the workflow clean."
        )

    if len(tasks) > 0 and not assigned:
        tip(
            f"{context} / List '{name}': No tasks have assignees. "
            "Assign owners to tasks for clear accountability."
        )

    return {
        "name": name,
        "task_count": task_count,
        "subtask_count": subtask_count,
        "statuses_used": statuses_used,
        "assignees": assigned,
    }


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


def generate_recommendations(meta: dict) -> None:
    """Generate best-practice recommendations based on validation metadata."""
    # Too many spaces
    if meta["space_count"] > MAX_SPACES_WARN:
        tip(
            f"Consider consolidating from {meta['space_count']} Spaces down to "
            f"{MAX_SPACES_WARN} or fewer. Common pattern: Marketing, Development, "
            "Operations, Delivery, and Personal."
        )

    # Too many distinct statuses across the workspace
    if len(meta["all_statuses"]) > 20:
        tip(
            f"Workspace uses {len(meta['all_statuses'])} distinct statuses across all Lists. "
            "Standardize on 3-5 statuses per workflow (e.g., To Do / In Progress / Done) "
            "and use Custom Field dropdowns for sub-stages. This keeps the Everything View readable."
        )

    # Empty lists
    if meta["lists_without_tasks"] > 0:
        tip(
            f"{meta['lists_without_tasks']} List(s) have no tasks. "
            "Either populate them or archive empty Lists to reduce clutter."
        )

    # All tasks unassigned
    if meta["task_count"] > 0 and not meta["assignee_counts"]:
        tip("No tasks have assignees. Assign owners to create accountability.")

    # Single assignee doing everything
    if len(meta["assignee_counts"]) == 1 and meta["task_count"] > 10:
        sole = list(meta["assignee_counts"].keys())[0]
        tip(
            f"All {meta['task_count']} assigned tasks belong to '{sole}'. "
            "Distribute work across the team to avoid burnout."
        )

    # Subtask usage
    if meta["task_count"] > 20 and meta["tasks_with_subtasks"] == 0:
        tip(
            "No tasks use subtasks. For complex work, break tasks into "
            "subtasks (up to 7 levels with Nested Subtasks ClickApp enabled)."
        )

    # Folder count
    if meta["folder_count"] > MAX_FOLDERS_WARN:
        tip(
            f"Workspace has {meta['folder_count']} Folders. If many are stale, "
            "archive unused Folders to keep navigation fast."
        )

    # Templates reminder
    if meta["space_count"] >= 3:
        tip(
            "You have multiple Spaces. Save templates for repeatable Space, Folder, "
            "and List structures to ensure consistency across new projects."
        )

    # Automations prompt
    if meta["task_count"] > 10:
        tip(
            f"With {meta['task_count']} tasks, consider setting up Automations for: "
            "status transitions, assignment routing, and due-date reminders. "
            "Start with one simple automation and iterate."
        )

    # Docs reminder
    if meta["list_count"] >= 5:
        tip(
            f"You have {meta['list_count']} Lists. Use ClickUp Docs for project specs, "
            "meeting notes, and wikis. Link Docs to tasks via Relationships for "
            "bidirectional traceability."
        )

    # No statuses defined at all
    if not meta["all_statuses"]:
        tip(
            "No statuses defined. Add status workflows to Lists to track task progress. "
            "Start with: To Do / In Progress / Done."
        )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def print_section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_report(meta: dict) -> None:
    """Print the full validation report."""
    print_section("CLICKUP WORKSPACE VALIDATION REPORT")
    print(f"  Workspace: {meta['name']}")
    print(f"  Spaces:    {meta['space_count']}")
    print(f"  Folders:   {meta['folder_count']}")
    print(f"  Lists:     {meta['list_count']}")
    print(f"  Tasks:     {meta['task_count']}")
    if meta["tasks_with_subtasks"] > 0:
        print(f"  Tasks with subtasks: {meta['tasks_with_subtasks']}")
    if meta["lists_without_tasks"] > 0:
        print(f"  Empty Lists: {meta['lists_without_tasks']}")

    if meta["status_counts"]:
        print_section("STATUS USAGE (across all Lists)")
        for status, count in meta["status_counts"].most_common():
            print(f"  {status}: {count} task(s)")

    if meta["assignee_counts"]:
        print_section("ASSIGNEE WORKLOAD")
        for person, count in meta["assignee_counts"].most_common():
            bar = "#" * min(count, 40)
            print(f"  {person:20s} {count:4d} tasks  {bar}")

    # --- Issues (blocking) ---
    if ISSUES:
        print_section(f"ISSUES ({len(ISSUES)})")
        for i, msg in enumerate(ISSUES, 1):
            print(f"  [{i}] {msg}")

    # --- Warnings ---
    if WARNINGS:
        print_section(f"WARNINGS ({len(WARNINGS)})")
        for i, msg in enumerate(WARNINGS, 1):
            print(f"  [{i}] {msg}")

    # --- Tips ---
    if TIPS:
        print_section(f"TIPS ({len(TIPS)})")
        for i, msg in enumerate(TIPS, 1):
            print(f"  [{i}] {msg}")

    # Summary
    print_section("SUMMARY")
    issue_count = len(ISSUES)
    warn_count = len(WARNINGS)
    tip_count = len(TIPS)

    if issue_count == 0 and warn_count == 0:
        print("  Workspace looks well-structured. Review the tips for further optimization.")
    elif issue_count > 0:
        print(f"  {issue_count} issue(s) found. Address these to fix structural problems.")
    if warn_count > 0:
        print(f"  {warn_count} warning(s). Review and fix where applicable.")
    print(f"  {tip_count} tip(s) provided for best practices.")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = ArgumentParser(
        description="Validate a ClickUp workspace structure from a JSON file.",
        epilog=(
            "Example JSON schema:\n"
            '  {"workspace": {"name": "...", "spaces": [{"name": "...", '
            '"folders": [{"name": "...", "lists": [{"name": "...", '
            '"statuses": [...], "tasks": [{"name": "...", "status": "...", '
            '"assignee": "...", "has_subtasks": false}]}]}]}]}}'
        ),
    )
    parser.add_argument(
        "input",
        type=str,
        help="Path to a JSON file describing the ClickUp workspace structure.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON instead of a human-readable report.",
    )
    args = parser.parse_args()

    if os.path.isfile(args.input):
        try:
            with open(args.input, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {args.input}: {e}", file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            print(f"Error: Cannot read {args.input}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Aceita JSON inline
        try:
            data = json.loads(args.input)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON: {e}", file=sys.stderr)
            sys.exit(1)

    workspace = data.get("workspace")
    if workspace is None:
        print(
            "Error: JSON must contain a top-level 'workspace' key.",
            file=sys.stderr,
        )
        sys.exit(1)

    meta = validate_workspace(workspace)
    generate_recommendations(meta)

    if args.json:
        output = {
            "workspace": meta["name"],
            "counts": {
                "spaces": meta["space_count"],
                "folders": meta["folder_count"],
                "lists": meta["list_count"],
                "tasks": meta["task_count"],
                "tasks_with_subtasks": meta["tasks_with_subtasks"],
                "empty_lists": meta["lists_without_tasks"],
            },
            "statuses": dict(meta["status_counts"].most_common()),
            "assignees": dict(meta["assignee_counts"].most_common()),
            "issues": ISSUES,
            "warnings": WARNINGS,
            "tips": TIPS,
        }
        print(json.dumps(output, indent=2))
    else:
        print_report(meta)

    sys.exit(0 if len(ISSUES) == 0 else 1)


if __name__ == "__main__":
    main()
