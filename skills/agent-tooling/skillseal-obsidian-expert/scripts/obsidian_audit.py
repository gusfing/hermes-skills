#!/usr/bin/env python3
"""
obsidian_audit.py -- Vault structure analyzer for Obsidian.

Analyzes an Obsidian vault directory and produces a health report covering
folder structure, link density, orphan notes, tag usage, frontmatter
completeness, and structural recommendations.

Part of the "obsidian-expert" skill.

Usage:
    python3 obsidian_audit.py /path/to/vault
    python3 obsidian_audit.py /path/to/vault --json

Output: plain-text audit report (default) or JSON (with --json).
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RECOMMENDED_FOLDERS = {
    "0-inbox",
    "1-fleeting",
    "2-literature",
    "3-permanent",
    "4-mocs",
    "5-projects",
    "6-archive",
    "_attachments",
    "_templates",
    "_scripts",
    "daily",
}

ESSENTIAL_FOLDERS = {
    "_attachments",
    "_templates",
    "daily",
}

HEALTHY_LINK_RANGE = (3, 50)   # min, max avg links per note
HEALTHY_TAG_COUNT = (10, 80)   # min, max unique tags
MAX_ORPHAN_PCT = 15.0          # max percentage of orphan notes
MIN_FRONTMATTER_PCT = 60.0     # min percentage with frontmatter


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------

def find_markdown_files(vault_path: Path) -> list[Path]:
    """Return all .md files in the vault, excluding .obsidian/ and dotfolders."""
    md_files = []
    for root, dirs, files in os.walk(vault_path):
        # skip hidden folders
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.endswith(".md"):
                md_files.append(Path(root) / f)
    return md_files


def parse_frontmatter(content: str) -> dict:
    """Extract YAML-style frontmatter from markdown content.

    Returns an empty dict if no frontmatter block is found.
    Handles basic YAML scalars, lists, and nested dicts (shallow).
    """
    if not content.startswith("---"):
        return {}

    end_idx = content.find("---", 3)
    if end_idx == -1:
        return {}

    fm_text = content[3:end_idx].strip()
    if not fm_text:
        return {}

    fm = {}
    current_key = None
    current_list = None

    for line in fm_text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # top-level key: value
        m = re.match(r"^(\w[\w_-]*)\s*:\s*(.*)", stripped)
        if m:
            current_key = m.group(1)
            val = m.group(2).strip().strip('"').strip("'")
            current_list = None
            if val == "":
                current_list = []
                fm[current_key] = current_list
            else:
                fm[current_key] = val
            continue

        # list item under current key
        if current_list is not None and stripped.startswith("- "):
            item = stripped[2:].strip().strip('"').strip("'")
            current_list.append(item)
            continue

    # Normalize tags: if tags is a string "tag1 tag2", split it
    if "tags" in fm and isinstance(fm["tags"], str):
        fm["tags"] = [t.strip() for t in fm["tags"].split() if t.strip()]

    return fm


def extract_wikilinks(content: str) -> list[str]:
    """Extract [[wikilink]] targets from content. Returns link target names."""
    return re.findall(r"\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]", content)


def extract_tags_from_content(content: str) -> list[str]:
    """Extract inline #tags from markdown content."""
    return re.findall(r"(?<!\w)#([a-zA-Z][\w/-]*)", content)


def analyze_vault(vault_path: str) -> dict:
    """Run full vault analysis and return a result dictionary."""
    vault = Path(vault_path).resolve()
    if not vault.exists() or not vault.is_dir():
        return {"error": f"Vault path does not exist or is not a directory: {vault_path}"}

    md_files = find_markdown_files(vault)

    # --- Folder analysis ---
    existing_dirs = set()
    all_dirs = set()
    for root, dirs, _ in os.walk(vault):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        rel = Path(root).relative_to(vault)
        for d in dirs:
            all_dirs.add(str(rel / d) if str(rel) != "." else d)
        if str(rel) != ".":
            existing_dirs.add(str(rel))

    # Also add empty top-level dirs that might not appear via os.walk
    for item in vault.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            existing_dirs.add(item.name)

    present_recommended = RECOMMENDED_FOLDERS & existing_dirs
    missing_recommended = RECOMMENDED_FOLDERS - existing_dirs
    missing_essential = ESSENTIAL_FOLDERS - existing_dirs

    # --- Per-note analysis ---
    total_notes = len(md_files)
    notes_with_frontmatter = 0
    notes_with_tags = 0
    notes_with_created = 0
    notes_with_aliases = 0
    all_tags: Counter = Counter()
    all_frontmatter_tags: Counter = Counter()
    total_links = 0
    notes_with_links = 0
    orphan_notes: list[str] = []
    stub_notes: list[str] = []
    stale_notes: list[str] = []
    note_link_counts: dict[str, int] = {}
    linked_to: Counter = Counter()  # how many notes link TO each target
    note_tags_map: dict[str, list] = {}
    notes_per_folder: Counter = Counter()
    dead_links: list[str] = []
    all_note_titles: set = {p.stem for p in md_files}

    six_months_ago = datetime.now() - timedelta(days=180)

    for md_path in md_files:
        rel_path = md_path.relative_to(vault)
        note_name = md_path.stem
        parent_folder = str(rel_path.parent) if str(rel_path.parent) != "." else "(root)"
        notes_per_folder[parent_folder] += 1

        try:
            content = md_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            content = ""

        # frontmatter
        fm = parse_frontmatter(content)
        has_fm = bool(fm)
        if has_fm:
            notes_with_frontmatter += 1
            if "created" in fm:
                notes_with_created += 1
            if "aliases" in fm:
                notes_with_aliases += 1
            if "tags" in fm and isinstance(fm["tags"], list):
                notes_with_tags += 1
                for t in fm["tags"]:
                    all_frontmatter_tags[t.strip()] += 1
                    all_tags[t.strip()] += 1
        else:
            # tags inline
            inline_tags = extract_tags_from_content(content)
            if inline_tags:
                notes_with_tags += 1
                for t in inline_tags:
                    all_tags[t] += 1

        # links
        links = extract_wikilinks(content)
        note_link_counts[note_name] = len(links)
        total_links += len(links)
        if links:
            notes_with_links += 1
        for link_target in links:
            linked_to[link_target] += 1

        # dead links: wikilink target that has no matching .md file
        for link_target in links:
            # alias-aware: strip alias part
            clean_target = link_target.split("|")[0].strip()
            if clean_target not in all_note_titles:
                dead_links.append(f"{note_name} -> [[{link_target}]]")

        # stub notes (empty body after frontmatter)
        body_start = 0
        if has_fm:
            end_idx = content.find("---", 3)
            body_start = end_idx + 3 if end_idx != -1 else 0
        body = content[body_start:].strip()
        if not body or body.startswith("# ") and len(body.split("\n")) <= 2:
            stub_notes.append(note_name)

        # stale notes (based on file mtime -- imperfect but useful approximation)
        try:
            mtime = datetime.fromtimestamp(md_path.stat().st_mtime)
            if mtime < six_months_ago:
                stale_notes.append(note_name)
        except OSError:
            pass

        note_tags_map[note_name] = (
            fm.get("tags", []) if isinstance(fm.get("tags"), list)
            else extract_tags_from_content(content)
        )

    # --- Orphan detection ---
    orphan_notes = []
    for note_name in note_link_counts:
        outgoing = note_link_counts[note_name]
        incoming = linked_to.get(note_name, 0)
        if outgoing == 0 and incoming == 0:
            orphan_notes.append(note_name)

    # --- Aggregate metrics ---
    avg_links = total_links / total_notes if total_notes else 0
    orphan_pct = (len(orphan_notes) / total_notes * 100) if total_notes else 0
    fm_pct = (notes_with_frontmatter / total_notes * 100) if total_notes else 0
    notes_without_links = total_notes - notes_with_links
    unique_tags = len(all_tags)
    unique_fm_tags = len(all_frontmatter_tags)
    tags_used_once = sum(1 for t, c in all_tags.items() if c == 1)
    stub_pct = (len(stub_notes) / total_notes * 100) if total_notes else 0

    # --- MOC coverage ---
    moc_folder_notes = set()
    for md_path in md_files:
        parent = str(md_path.relative_to(vault).parent)
        if "moc" in parent.lower():
            moc_folder_notes.add(md_path.stem)
    moc_linked_notes = set(linked_to.keys())
    permanent_notes = set()
    for md_path in md_files:
        parent = str(md_path.relative_to(vault).parent)
        if "permanent" in parent.lower():
            permanent_notes.add(md_path.stem)
    moc_coverage = (
        len(permanent_notes & moc_linked_notes) / len(permanent_notes) * 100
        if permanent_notes else 0
    )

    # --- Generate recommendations ---
    recommendations = []

    if missing_essential:
        recommendations.append(
            f"Create essential folders: {', '.join(sorted(missing_essential))}"
        )

    if orphan_pct > MAX_ORPHAN_PCT:
        recommendations.append(
            f"Reduce orphan notes ({len(orphan_notes)} notes, "
            f"{orphan_pct:.1f}%): link them to MOCs or related notes, "
            "or archive/delete if no longer relevant"
        )

    if avg_links < HEALTHY_LINK_RANGE[0]:
        recommendations.append(
            f"Increase link density (current avg: {avg_links:.1f} links/note, "
            f"target: >={HEALTHY_LINK_RANGE[0]}). "
            "Add [[wikilinks]] to connect related concepts"
        )

    if avg_links > HEALTHY_LINK_RANGE[1]:
        recommendations.append(
            f"Link density is very high ({avg_links:.1f} links/note). "
            "Consider whether some links can be consolidated via MOCs"
        )

    if fm_pct < MIN_FRONTMATTER_PCT:
        recommendations.append(
            f"Improve frontmatter coverage ({fm_pct:.1f}% have frontmatter, "
            f"target: >={MIN_FRONTMATTER_PCT}%). "
            "Use a template with 'created' and 'tags' fields"
        )

    if unique_tags > HEALTHY_TAG_COUNT[1]:
        recommendations.append(
            f"Reduce tag sprawl ({unique_tags} unique tags, "
            f"{tags_used_once} used only once). "
            "Consolidate similar tags and remove unused ones"
        )

    if unique_tags < HEALTHY_TAG_COUNT[0] and total_notes > 20:
        recommendations.append(
            f"Consider more tag granularity ({unique_tags} unique tags for "
            f"{total_notes} notes). Tags help Dataview queries surface content"
        )

    if stub_pct > 10:
        recommendations.append(
            f"Fill in or remove stub notes ({len(stub_notes)} notes, "
            f"{stub_pct:.1f}%). Empty notes add noise to search and graph"
        )

    if dead_links:
        recommendations.append(
            f"Fix {len(dead_links)} dead link(s): wikilinks pointing to "
            "notes that do not exist. Either create the missing note or "
            "remove the link"
        )

    if stale_notes and len(stale_notes) / total_notes > 0.5:
        recommendations.append(
            f"Review stale notes ({len(stale_notes)} notes untouched "
            "for 6+ months). Archive or refresh them"
        )

    # --- Grade ---
    score = 100.0
    if orphan_pct > MAX_ORPHAN_PCT:
        score -= min(30, (orphan_pct - MAX_ORPHAN_PCT) * 2)
    if fm_pct < MIN_FRONTMATTER_PCT:
        score -= min(25, (MIN_FRONTMATTER_PCT - fm_pct) * 1.5)
    if avg_links < HEALTHY_LINK_RANGE[0]:
        score -= min(20, (HEALTHY_LINK_RANGE[0] - avg_links) * 5)
    if unique_tags > HEALTHY_TAG_COUNT[1]:
        score -= min(15, (unique_tags - HEALTHY_TAG_COUNT[1]) * 0.5)
    if stub_pct > 10:
        score -= min(10, stub_pct)
    if missing_essential:
        score -= len(missing_essential) * 5
    if dead_links:
        score -= min(10, len(dead_links) * 0.5)

    score = max(0, round(score))

    if score >= 85:
        grade = "A -- Excellent"
    elif score >= 70:
        grade = "B -- Good"
    elif score >= 55:
        grade = "C -- Fair"
    elif score >= 40:
        grade = "D -- Needs Work"
    else:
        grade = "F -- Critical Issues"

    result = {
        "vault_path": str(vault),
        "analysis_timestamp": datetime.now().isoformat(),
        "summary": {
            "total_notes": total_notes,
            "health_score": score,
            "grade": grade,
        },
        "folder_structure": {
            "present_recommended": sorted(present_recommended),
            "missing_recommended": sorted(missing_recommended),
            "missing_essential": sorted(missing_essential),
        },
        "link_metrics": {
            "total_links": total_links,
            "avg_links_per_note": round(avg_links, 2),
            "notes_with_links": notes_with_links,
            "notes_without_links": notes_without_links,
            "orphan_notes_count": len(orphan_notes),
            "orphan_percentage": round(orphan_pct, 1),
            "orphan_notes": sorted(orphan_notes),
            "dead_links_count": len(dead_links),
            "dead_links_sample": dead_links[:10],
        },
        "tag_metrics": {
            "unique_tags_fm": unique_fm_tags,
            "unique_tags_total": unique_tags,
            "notes_with_tags": notes_with_tags,
            "tags_used_once": tags_used_once,
            "top_tags": all_tags.most_common(15),
        },
        "frontmatter_metrics": {
            "notes_with_frontmatter": notes_with_frontmatter,
            "frontmatter_percentage": round(fm_pct, 1),
            "notes_with_created": notes_with_created,
            "notes_with_aliases": notes_with_aliases,
        },
        "content_health": {
            "stub_notes_count": len(stub_notes),
            "stub_percentage": round(stub_pct, 1),
            "stale_notes_count": len(stale_notes),
            "stale_percentage": (
                round(len(stale_notes) / total_notes * 100, 1)
                if total_notes else 0
            ),
        },
        "recommendations": recommendations,
        "notes_per_folder": dict(notes_per_folder.most_common()),
    }

    return result


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def format_report(result: dict) -> str:
    """Format the analysis result as a human-readable report."""
    if "error" in result:
        return f"ERROR: {result['error']}"

    s = result["summary"]
    fs = result["folder_structure"]
    lm = result["link_metrics"]
    tm = result["tag_metrics"]
    fm_m = result["frontmatter_metrics"]
    ch = result["content_health"]
    recs = result["recommendations"]

    lines = []
    lines.append("=" * 60)
    lines.append("OBSIDIAN VAULT AUDIT REPORT")
    lines.append("=" * 60)
    lines.append(f"Vault: {result['vault_path']}")
    lines.append(f"Analyzed: {result['analysis_timestamp'][:19]}")
    lines.append("")

    # Score
    lines.append(f"HEALTH SCORE: {s['health_score']}/100 -- {s['grade']}")
    lines.append(f"Total Notes: {s['total_notes']}")
    lines.append("")

    # Folder structure
    lines.append("-" * 60)
    lines.append("FOLDER STRUCTURE")
    lines.append("-" * 60)
    if fs["present_recommended"]:
        lines.append(f"  Present: {', '.join(fs['present_recommended'])}")
    else:
        lines.append("  Present: (none of the recommended folders found)")
    if fs["missing_recommended"]:
        lines.append(f"  Missing (recommended): {', '.join(fs['missing_recommended'])}")
    if fs["missing_essential"]:
        lines.append(f"  Missing (essential): {', '.join(fs['missing_essential'])}")
    lines.append("")

    # Link metrics
    lines.append("-" * 60)
    lines.append("LINK METRICS")
    lines.append("-" * 60)
    lines.append(f"  Total wikilinks:       {lm['total_links']}")
    lines.append(f"  Average links/note:    {lm['avg_links_per_note']}")
    lines.append(f"  Notes with links:      {lm['notes_with_links']}")
    lines.append(f"  Notes without links:   {lm['notes_without_links']}")
    lines.append(f"  Orphan notes:          {lm['orphan_notes_count']} ({lm['orphan_percentage']}%)")
    if lm["orphan_notes"]:
        orphans_display = ", ".join(lm["orphan_notes"][:10])
        if len(lm["orphan_notes"]) > 10:
            orphans_display += f" ... and {len(lm['orphan_notes']) - 10} more"
        lines.append(f"    Orphans: {orphans_display}")
    lines.append(f"  Dead links:            {lm['dead_links_count']}")
    if lm["dead_links_sample"]:
        for dl in lm["dead_links_sample"][:5]:
            lines.append(f"    {dl}")
    lines.append("")

    # Tag metrics
    lines.append("-" * 60)
    lines.append("TAG METRICS")
    lines.append("-" * 60)
    lines.append(f"  Unique tags (frontmatter): {tm['unique_tags_fm']}")
    lines.append(f"  Unique tags (total):       {tm['unique_tags_total']}")
    lines.append(f"  Notes with tags:           {tm['notes_with_tags']}")
    lines.append(f"  Tags used only once:       {tm['tags_used_once']}")
    if tm["top_tags"]:
        top = ", ".join(f"#{t}({c})" for t, c in tm["top_tags"][:10])
        lines.append(f"  Top tags: {top}")
    lines.append("")

    # Frontmatter metrics
    lines.append("-" * 60)
    lines.append("FRONTMATTER METRICS")
    lines.append("-" * 60)
    lines.append(f"  Notes with frontmatter: {fm_m['notes_with_frontmatter']} ({fm_m['frontmatter_percentage']}%)")
    lines.append(f"  Notes with 'created':   {fm_m['notes_with_created']}")
    lines.append(f"  Notes with 'aliases':   {fm_m['notes_with_aliases']}")
    lines.append("")

    # Content health
    lines.append("-" * 60)
    lines.append("CONTENT HEALTH")
    lines.append("-" * 60)
    lines.append(f"  Stub notes:             {ch['stub_notes_count']} ({ch['stub_percentage']}%)")
    lines.append(f"  Stale notes (6m+):      {ch['stale_notes_count']} ({ch['stale_percentage']}%)")
    lines.append("")

    # Recommendations
    lines.append("-" * 60)
    lines.append("RECOMMENDATIONS")
    lines.append("-" * 60)
    if recs:
        for i, rec in enumerate(recs, 1):
            lines.append(f"  {i}. {rec}")
    else:
        lines.append("  No recommendations. Vault looks healthy.")
    lines.append("")

    # Notes per folder
    npf = result.get("notes_per_folder", {})
    if npf:
        lines.append("-" * 60)
        lines.append("NOTES PER FOLDER")
        lines.append("-" * 60)
        for folder, count in sorted(npf.items()):
            lines.append(f"  {folder}: {count}")
        lines.append("")

    lines.append("=" * 60)
    lines.append(f"VERDICT: {s['grade']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: python3 obsidian_audit.py /path/to/vault [--json]")
        print()
        print("Analyze an Obsidian vault and produce a health report.")
        print()
        print("Options:")
        print("  --json       Output results as JSON instead of a text report")
        print("  -h, --help   Show this help message")
        sys.exit(0)

    vault_path = sys.argv[1]
    output_json = "--json" in sys.argv

    # Se não for um diretório existente, cria um mini-vault de exemplo em temp
    if not os.path.isdir(vault_path):
        import tempfile
        tmp_vault = Path(tempfile.mkdtemp(prefix="obsidian_vault_"))
        (tmp_vault / "Inbox").mkdir(exist_ok=True)
        (tmp_vault / "Projects").mkdir(exist_ok=True)
        (tmp_vault / "Notes").mkdir(exist_ok=True)
        (tmp_vault / "Inbox" / "note-1.md").write_text(
            "---\ntags: [inbox]\ncreated: 2026-01-01\n---\n# Note 1\n\nContent with a [[link]].\n",
            encoding="utf-8",
        )
        (tmp_vault / "Projects" / "note-2.md").write_text(
            "# Note 2\n\nLinked to [[note-1]]. No frontmatter here.\n",
            encoding="utf-8",
        )
        (tmp_vault / "Notes" / "note-3.md").write_text(
            "# Note 3\n\nOrphan note with no links.\n",
            encoding="utf-8",
        )
        vault_path = str(tmp_vault)

    result = analyze_vault(vault_path)

    if output_json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(format_report(result))

    if "error" in result:
        sys.exit(1)
    elif result["summary"]["health_score"] < 40:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
