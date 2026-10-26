#!/usr/bin/env python3
"""
Instagram Metrics Audit Tool - insta_audit.py
=============================================
Analyzes Instagram account metrics and surfaces problems and opportunities.

Accepts metrics as:
  1. Inline JSON string:  python insta_audit.py '{"followers": 5000, ...}'
  2. JSON file path:      python insta_audit.py metrics.json

Outputs a structured audit report with severity levels, benchmarks,
and actionable recommendations.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Benchmark constants
# ---------------------------------------------------------------------------

ENGAGEMENT_RATE_BENCHMARKS = {
    (0, 5000):       (3.0, 6.0),    # 1K-5K followers
    (5000, 20000):   (2.0, 4.0),    # 5K-20K
    (20000, 100000): (1.5, 3.0),    # 20K-100K
    (100000, 1000000): (1.0, 2.0),  # 100K-1M
    (1000000, float("inf")): (0.5, 1.5),  # 1M+
}

STORY_EXIT_THRESHOLD = 10.0          # Above 10% exits is a red flag
COMPLETION_RATE_THRESHOLD = 50.0     # Below 50% is weak
REACH_IMPRESSIONS_RATIO_MIN = 1.5    # Below 1.5x means low reach expansion
IMPRESSIONS_REACH_RATIO_MAX = 2.0
FOLLOWER_GROWTH_MONTHLY_MIN = 2.0    # Below 2% monthly is slow
SAVES_SHARE_PCT_MIN = 5.0            # Saves should be ~5% of total engagement
SHARES_PCT_MIN = 2.0                 # Shares should be ~2% of total engagement


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_metrics(source: str) -> Dict:
    """Load metrics from a JSON string or a file path.

    Uses os.path.isfile() to distinguish between inline JSON and file paths.
    """
    # Check if source looks like a file path (ends with .json or contains path separators)
    looks_like_file = source.endswith(".json") or "/" in source
    if looks_like_file:
        if os.path.isfile(source):
            with open(source, "r") as fh:
                return json.load(fh)
        raise FileNotFoundError(
            f"File not found: '{source}'. If you meant to pass inline JSON, "
            f"wrap it in single quotes and ensure it does not look like a filename."
        )
    return json.loads(source)


def get_engagement_benchmark(followers: int) -> Tuple[float, float]:
    """Return (min_healthy, target) engagement rate for a given follower count."""
    for (lo, hi), (min_er, target_er) in ENGAGEMENT_RATE_BENCHMARKS.items():
        if lo <= followers < hi:
            return min_er, target_er
    return (0.5, 1.5)  # fallback for 0 followers or extreme counts


def calc_engagement_rate(data: Dict) -> Optional[float]:
    """Calculate engagement rate: (likes+comments+saves+shares)/followers*100."""
    followers = data.get("followers", 0)
    if followers <= 0:
        return None
    total = (
        data.get("likes", 0)
        + data.get("comments", 0)
        + data.get("saves", 0)
        + data.get("shares", 0)
    )
    return round(total / followers * 100, 2)


def severity_label(value: float, thresholds: Tuple[float, float, float]) -> str:
    """Classify value as good / warning / critical based on thresholds.

    thresholds = (good_above, warn_below, critical_below)
    """
    good, warn, crit = thresholds
    if value >= good:
        return "good"
    if value >= crit:
        return "warning"
    return "critical"


# ---------------------------------------------------------------------------
# Audit checks
# ---------------------------------------------------------------------------

class AuditIssue:
    """A single finding from the audit."""

    def __init__(self, area: str, severity: str, message: str, recommendation: str):
        self.area = area
        self.severity = severity   # good | warning | critical
        self.message = message
        self.recommendation = recommendation


def check_engagement_rate(data: Dict, followers: int) -> List[AuditIssue]:
    issues = []
    er = calc_engagement_rate(data)
    if er is None:
        issues.append(AuditIssue(
            "Engagement Rate", "critical",
            "Cannot calculate engagement rate: follower count is zero or missing.",
            "Provide a valid 'followers' value in your metrics data."
        ))
        return issues

    min_er, target_er = get_engagement_benchmark(followers)

    if er >= target_er:
        sev = "good"
        msg = (f"Engagement rate is {er}% -- above the target of {target_er}% "
               f"for accounts with {followers} followers.")
        rec = "Keep doing what you are doing. Analyze top posts to identify what drives this rate."
    elif er >= min_er:
        sev = "warning"
        msg = (f"Engagement rate is {er}% -- within range [{min_er}%-{target_er}%] "
               f"but below the target for your tier.")
        rec = ("Improve content hooks, add CTAs in captions, and respond to every comment "
               "within the first hour after posting.")
    else:
        sev = "critical"
        msg = (f"Engagement rate is {er}% -- below the minimum healthy threshold "
               f"of {min_er}% for accounts with {followers} followers.")
        rec = ("Audit your last 10 posts. If they all have low engagement, you may have "
               "ghost followers or content that does not resonate. Test Reels with trending "
               "audio and strong hooks. Consider an audience cleanup.")

    issues.append(AuditIssue("Engagement Rate", sev, msg, rec))
    return issues


def check_reach_impressions(data: Dict) -> List[AuditIssue]:
    issues = []
    reach = data.get("reach", 0)
    impressions = data.get("impressions", 0)

    if reach <= 0:
        issues.append(AuditIssue(
            "Reach/Impressions", "warning",
            "Reach data is missing or zero. Cannot evaluate audience expansion.",
            "Provide 'reach' and 'impressions' fields in your metrics."
        ))
        return issues

    ratio = impressions / reach

    if ratio >= REACH_IMPRESSIONS_RATIO_MIN:
        sev = "good"
        msg = (f"Impressions-to-reach ratio is {ratio:.1f}x -- healthy. "
               f"Your audience is seeing your content multiple times.")
        rec = "Maintain consistency. Experiment with posting at different times."
    else:
        sev = "warning"
        msg = (f"Impressions-to-reach ratio is {ratio:.1f}x -- below the {REACH_IMPRESSIONS_RATIO_MIN}x target. "
               f"Your content is not being shown multiple times to the same users.")
        rec = ("Post more Stories and carousels to increase touch frequency. "
               "Users need multiple exposures before taking action.")

    issues.append(AuditIssue("Reach/Impressions", sev, msg, rec))
    return issues


def check_completion_rate(data: Dict) -> List[AuditIssue]:
    issues = []
    rate = data.get("completion_rate")
    if rate is None:
        return issues  # optional metric, skip if absent

    if rate >= COMPLETION_RATE_THRESHOLD:
        sev = "good"
        msg = f"Reel completion rate is {rate}% -- strong retention."
        rec = "Test longer Reels (30-60s) to tell deeper stories. You have attention."
    else:
        sev = "critical"
        msg = f"Reel completion rate is {rate}% -- below the {COMPLETION_RATE_THRESHOLD}% target."
        rec = ("Shorten your Reels to 7-15 seconds. Improve the first-3-second hook. "
               "Ensure captions are on screen. Avoid slow intros.")
    issues.append(AuditIssue("Reel Completion Rate", sev, msg, rec))
    return issues


def check_story_exits(data: Dict) -> List[AuditIssue]:
    issues = []
    exits = data.get("story_exit_rate")
    if exits is None:
        return issues

    if exits <= STORY_EXIT_THRESHOLD:
        sev = "good"
        msg = f"Story exit rate is {exits}% -- within healthy range (below {STORY_EXIT_THRESHOLD}%)."
        rec = "Keep your Story cadence. Add interactive stickers to boost engagement."
    else:
        sev = "critical"
        msg = f"Story exit rate is {exits}% -- above the {STORY_EXIT_THRESHOLD}% threshold."
        rec = ("Your first 1-2 Stories are causing drop-offs. Make the first Story a strong hook. "
               "Reduce Story volume to avoid fatigue. Check if content is repetitive.")
    issues.append(AuditIssue("Story Exits", sev, msg, rec))
    return issues


def check_follower_growth(data: Dict) -> List[AuditIssue]:
    issues = []
    growth_pct = data.get("follower_growth_rate")
    if growth_pct is None:
        issues.append(AuditIssue(
            "Follower Growth", "warning",
            "Follower growth rate is not provided. Cannot assess growth trajectory.",
            "Provide 'follower_growth_rate' (monthly percentage) in your metrics."
        ))
        return issues

    if growth_pct >= FOLLOWER_GROWTH_MONTHLY_MIN:
        sev = "good"
        msg = f"Monthly follower growth is {growth_pct}% -- healthy organic pace."
        rec = "Sustain current strategy. Identify which content types drive the most new follows."
    else:
        sev = "warning"
        msg = f"Monthly follower growth is {growth_pct}% -- below the {FOLLOWER_GROWTH_MONTHLY_MIN}% target."
        rec = ("Increase Reel output to 3-5 per week. Use trending audio. "
               "Collaborate with similar-sized accounts for cross-exposure.")
    issues.append(AuditIssue("Follower Growth", sev, msg, rec))
    return issues


def check_engagement_composition(data: Dict) -> List[AuditIssue]:
    issues = []
    likes = data.get("likes", 0)
    comments = data.get("comments", 0)
    saves = data.get("saves", 0)
    shares = data.get("shares", 0)
    total = likes + comments + saves + shares

    if total == 0:
        return issues

    saves_pct = saves / total * 100
    shares_pct = shares / total * 100

    if saves_pct < SAVES_SHARE_PCT_MIN:
        issues.append(AuditIssue(
            "Saves Rate", "warning",
            f"Saves represent only {saves_pct:.1f}% of total engagement (target: {SAVES_SHARE_PCT_MIN}%+).",
            "Create save-worthy content: checklists, carousels with actionable steps, tutorials. "
            "Add a direct CTA: 'Save this for later.'"
        ))

    if shares_pct < SHARES_PCT_MIN and total > 50:
        issues.append(AuditIssue(
            "Shares Rate", "warning",
            f"Shares represent only {shares_pct:.1f}% of total engagement (target: {SHARES_PCT_MIN}%+).",
            "Create relatable or surprising content people want to send to friends. "
            "Use humor, hot takes, or highly specific niche observations."
        ))

    comments_pct = comments / total * 100
    if comments_pct < 3.0 and total > 50:
        issues.append(AuditIssue(
            "Comments Rate", "warning",
            f"Comments represent only {comments_pct:.1f}% of engagement.",
            "End captions with an open-ended question. Reply to comments with 4+ words. "
            "Avoid yes/no questions -- ask for opinions or experiences."
        ))

    return issues


def check_hashtag_strategy(data: Dict) -> List[AuditIssue]:
    issues = []
    hashtags = data.get("hashtags_used", data.get("hashtags"))

    if hashtags is None:
        return issues

    if isinstance(hashtags, str):
        hashtags = [h.strip() for h in hashtags.replace("#", "").split(",") if h.strip()]

    if isinstance(hashtags, list):
        count = len(hashtags)
        if count == 0:
            issues.append(AuditIssue(
                "Hashtags", "critical",
                "No hashtags are being used. You are invisible to non-followers.",
                "Use 5-10 relevant hashtags per post: mix broad (2-3), niche (3-5), and branded (1-2)."
            ))
        elif count > 20:
            issues.append(AuditIssue(
                "Hashtags", "critical",
                f"Using {count} hashtags -- Instagram may flag this as spam.",
                "Reduce to 5-10 highly relevant hashtags. Place them in the first comment."
            ))
        elif count < 3:
            issues.append(AuditIssue(
                "Hashtags", "warning",
                f"Only {count} hashtag(s) used -- limited discovery potential.",
                "Add 3-5 niche hashtags where your target audience spends time."
            ))
    return issues


def check_posting_frequency(data: Dict) -> List[AuditIssue]:
    issues = []
    posts_per_week = data.get("posts_per_week")
    stories_per_day = data.get("stories_per_day")
    reels_per_week = data.get("reels_per_week")

    if posts_per_week is not None:
        if posts_per_week < 3:
            issues.append(AuditIssue(
                "Posting Frequency", "critical",
                f"Only {posts_per_week} feed post(s) per week -- below the minimum of 3.",
                "Aim for at least 3 feed posts per week. Batch-create content on a dedicated day."
            ))
        elif posts_per_week >= 5:
            pass  # healthy
        else:
            issues.append(AuditIssue(
                "Posting Frequency", "warning",
                f"{posts_per_week} feed posts per week. Increase to 5+ for faster growth.",
                "Add one more post per week. Use carousels -- they get higher reach than static images."
            ))

    if reels_per_week is not None:
        if reels_per_week < 2:
            issues.append(AuditIssue(
                "Reels Output", "critical",
                f"Only {reels_per_week} Reel(s) per week. Reels are the main growth format.",
                "Post at least 2-3 Reels per week. Repurpose top-performing static posts as Reels."
            ))

    if stories_per_day is not None:
        if stories_per_day < 3:
            issues.append(AuditIssue(
                "Stories Cadence", "warning",
                f"Only {stories_per_day} Stories per day -- you are barely visible between feed posts.",
                "Post 5-10 Stories daily. Use polls, questions, and behind-the-scenes content."
            ))
    return issues


def check_profile_completeness(data: Dict) -> List[AuditIssue]:
    issues = []

    bio = data.get("bio", "")
    if not bio or len(bio) < 20:
        issues.append(AuditIssue(
            "Profile Bio", "critical",
            "Bio is missing or too short (less than 20 characters).",
            "Use the formula: [What you do] + [For whom] + [Result] + [CTA]. Max 150 characters."
        ))

    has_link = data.get("link_in_bio") or data.get("website")
    if not has_link:
        issues.append(AuditIssue(
            "Link in Bio", "warning",
            "No link in bio detected. You are missing a conversion opportunity.",
            "Add a Linktree, Beacons page, or your website URL. Use the only clickable link wisely."
        ))

    highlights = data.get("story_highlights", data.get("highlights", 0))
    if isinstance(highlights, (int, float)) and highlights < 3:
        issues.append(AuditIssue(
            "Story Highlights", "warning",
            f"Only {int(highlights)} highlight(s) active. Highlights serve as your portfolio.",
            "Create at least 4 highlights: About, Services, Results, and FAQ. Add covers for branding."
        ))

    profile_pic = data.get("profile_photo", data.get("profile_pic", True))
    if not profile_pic:
        issues.append(AuditIssue(
            "Profile Photo", "critical",
            "No profile photo detected.",
            "Add a clear face photo or logo. Minimum 500x500 pixels, clean background."
        ))

    return issues


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def run_audit(data: Dict) -> str:
    """Run all checks and return a formatted audit report."""

    followers = data.get("followers", 0)
    username = data.get("username", data.get("handle", "unknown"))

    lines = []
    lines.append("=" * 64)
    lines.append("  INSTAGRAM METRICS AUDIT REPORT")
    lines.append(f"  Account: @{username}")
    lines.append(f"  Followers: {followers:,}")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 64)
    lines.append("")

    # Summary metrics
    er = calc_engagement_rate(data)
    if er is not None:
        min_er, target_er = get_engagement_benchmark(followers)
        lines.append(f"  Engagement Rate: {er}%  (benchmark: {min_er}%-{target_er}%)")
    lines.append("")

    # Run all checks
    all_issues: List[AuditIssue] = []
    all_issues.extend(check_engagement_rate(data, followers))
    all_issues.extend(check_reach_impressions(data))
    all_issues.extend(check_completion_rate(data))
    all_issues.extend(check_story_exits(data))
    all_issues.extend(check_follower_growth(data))
    all_issues.extend(check_engagement_composition(data))
    all_issues.extend(check_hashtag_strategy(data))
    all_issues.extend(check_posting_frequency(data))
    all_issues.extend(check_profile_completeness(data))

    # Group by severity
    criticals = [i for i in all_issues if i.severity == "critical"]
    warnings = [i for i in all_issues if i.severity == "warning"]
    goods = [i for i in all_issues if i.severity == "good"]

    # Score
    total = len(all_issues) or 1
    score = round((len(goods) * 10 + len(warnings) * 5) / total * 10)
    lines.append(f"  OVERALL HEALTH SCORE: {score}/100")
    lines.append(f"  Critical: {len(criticals)} | Warnings: {len(warnings)} | Good: {len(goods)}")
    lines.append("")

    # Section: Critical issues
    if criticals:
        lines.append("-" * 64)
        lines.append("  [CRITICAL] Issues requiring immediate attention")
        lines.append("-" * 64)
        for i, issue in enumerate(criticals, 1):
            lines.append(f"  {i}. [{issue.area}] {issue.message}")
            lines.append(f"     FIX: {issue.recommendation}")
            lines.append("")
    else:
        lines.append("  No critical issues found. Good job.")
        lines.append("")

    # Section: Warnings
    if warnings:
        lines.append("-" * 64)
        lines.append("  [WARNING] Opportunities for improvement")
        lines.append("-" * 64)
        for i, issue in enumerate(warnings, 1):
            lines.append(f"  {i}. [{issue.area}] {issue.message}")
            lines.append(f"     ACTION: {issue.recommendation}")
            lines.append("")

    # Section: What is working well
    if goods:
        lines.append("-" * 64)
        lines.append("  [GOOD] What is working well")
        lines.append("-" * 64)
        for i, issue in enumerate(goods, 1):
            lines.append(f"  {i}. [{issue.area}] {issue.message}")
            lines.append("")

    # Summary recommendation
    lines.append("=" * 64)
    lines.append("  TOP PRIORITY ACTIONS")
    lines.append("=" * 64)
    priority = criticals + warnings
    for i, issue in enumerate(priority[:5], 1):
        lines.append(f"  {i}. [{issue.area}] {issue.recommendation}")

    lines.append("")
    lines.append("=" * 64)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: insta_audit.py <json_string_or_file_path>")
        print()
        print("Examples:")
        print('  insta_audit.py \'{"followers": 5000, "likes": 300, "comments": 50, ...}\'')
        print("  insta_audit.py metrics.json")
        sys.exit(1)

    source = sys.argv[1]

    try:
        data = load_metrics(source)
    except (json.JSONDecodeError, FileNotFoundError) as exc:
        print(f"Error loading metrics: {exc}", file=sys.stderr)
        sys.exit(1)

    report = run_audit(data)
    print(report)


if __name__ == "__main__":
    main()
