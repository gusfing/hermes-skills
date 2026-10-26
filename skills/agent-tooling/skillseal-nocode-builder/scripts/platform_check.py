#!/usr/bin/env python3
"""
platform_check.py -- No-Code Platform Recommendation Engine
Analyzes a project requirement description and suggests the best no-code or low-code platform.
Part of the "nocode-builder" skill.

Usage:
    python3 platform_check.py "I need a customer web app with user logins and payments"
    python3 platform_check.py --format json "Build an internal dashboard for operations"
    echo "Build a mobile app for field workers" | python3 platform_check.py -
    python3 platform_check.py --help
"""

import argparse
import json
import sys
from collections import OrderedDict


# Platform profiles: (keywords, weight) tuples
# Each platform gets scored based on keyword matches in the requirement text.
# Keywords are grouped by category to prevent single-keyword bias.
PLATFORMS = OrderedDict([
    ("Bubble", {
        "display": "Bubble",
        "description": "Full-stack no-code web application builder with built-in database, user authentication, and responsive design. Best for customer-facing web apps.",
        "keywords": {
            "web_app": [
                "web app", "web application", "website", "saas", "marketplace",
                "social network", "customer-facing", "customer facing", "consumer",
                "online platform", "web portal", "responsive", "desktop browser"
            ],
            "complex_ui": [
                "user login", "authentication", "sign up", "user account",
                "stripe", "payment", "subscription", "dashboard", "workflow",
                "drag and drop", "custom ui", "rich interface", "onboarding",
                "multi-step", "multi step", "user role", "permission", "access control"
            ],
            "database_logic": [
                "database", "data model", "crud", "search", "filter",
                "real-time", "live update", "notification", "messaging",
                "profile", "listing", "content management", "cms"
            ],
        },
        "anti_keywords": [
            "mobile app", "native app", "ios", "android", "play store",
            "internal tool", "admin panel", "internal dashboard",
            "no database", "simple form", "one-page"
        ],
    }),
    ("Glide", {
        "display": "Glide",
        "description": "Mobile-first no-code platform that turns spreadsheets into progressive web apps. Best for field teams, simple data collection, and mobile workflows.",
        "keywords": {
            "mobile": [
                "mobile", "phone", "tablet", "smartphone", "on the go",
                "field", "mobile app", "progressive web app", "pwa",
                "ios", "android", "app store", "play store", "downloadable"
            ],
            "simple_data": [
                "spreadsheet", "google sheet", "excel", "csv", "simple data",
                "log", "check-in", "check in", "inspection", "survey",
                "inventory", "catalog", "directory", "employee list",
                "tracking", "track", "quick app", "simple app",
            ],
            "field_work": [
                "field worker", "delivery", "driver", "technician",
                "inspection", "site visit", "onsite", "on-site",
                "scan", "barcode", "qr code", "photo upload",
                "gps", "location", "site"
            ],
        },
        "anti_keywords": [
            "complex logic", "api integration", "backend", "admin panel",
            "saas", "marketplace", "payment gateway", "complex dashboard",
            "real-time", "enterprise", "thousands of users"
        ],
    }),
    ("Retool", {
        "display": "Retool",
        "description": "Low-code platform for building internal tools, admin panels, and operational dashboards connected to existing databases and APIs.",
        "keywords": {
            "internal": [
                "internal", "admin", "operations", "back office", "back-office",
                "internal tool", "internal dashboard", "admin panel", "admin dashboard",
                "employee tool", "staff", "team tool", "operational"
            ],
            "database_connect": [
                "postgres", "postgresql", "mysql", "sql", "bigquery",
                "mongodb", "existing database", "connect to", "database connection",
                "snowflake", "redshift", "data warehouse"
            ],
            "data_heavy": [
                "data viz", "data visualization", "chart", "graph",
                "report", "analytics", "metrics", "kpi", "sql query",
                "crud interface", "data table", "data grid", "bulk edit",
                "export", "csv export", "reporting"
            ],
        },
        "anti_keywords": [
            "customer-facing", "customer facing", "consumer", "public",
            "end user", "end-user", "mobile-first", "mobile first",
            "spreadsheet", "simple form", "no database"
        ],
    }),
    ("Airtable", {
        "display": "Airtable",
        "description": "Spreadsheet-database hybrid with automations and interfaces. Best for content management, project tracking, and lightweight CRM.",
        "keywords": {
            "spreadsheet": [
                "spreadsheet", "google sheet", "excel", "table", "grid",
                "rows and columns", "csv import", "data entry"
            ],
            "content_management": [
                "content calendar", "editorial", "blog", "content",
                "project tracker", "task list", "to-do", "todo list",
                "crm", "pipeline", "lead", "contact management",
                "inventory", "catalog", "asset library"
            ],
            "lightweight": [
                "lightweight", "simple database", "prototype", "mvp data",
                "small team", "start small", "proof of concept",
                "no code", "non-technical", "easy to use", "collaborative",
                "shared", "team collaboration"
            ],
        },
        "anti_keywords": [
            "complex logic", "backend automation", "api orchestration",
            "thousands of users", "high traffic", "real-time sync",
            "payment processing", "authentication", "user login",
            "public web app"
        ],
    }),
    ("n8n", {
        "display": "n8n",
        "description": "Self-hostable workflow automation platform connecting APIs, databases, and services through visual workflows. Best for backend automation and API orchestration.",
        "keywords": {
            "automation": [
                "automation", "automate", "workflow", "orchestrate",
                "orchestration", "pipeline", "integrate", "integration",
                "connect", "sync", "synchronize", "trigger", "webhook"
            ],
            "backend": [
                "backend", "api", "rest api", "server-side", "server side",
                "background job", "cron", "scheduled", "batch processing",
                "data pipeline", "etl"
            ],
            "self_hosted": [
                "self-host", "self host", "self-hosted", "docker", "on-premise",
                "on premise", "private server", "data privacy", "compliance",
                "hipaa", "gdpr", "sensitive data"
            ],
            "multi_service": [
                "multiple services", "connect apps", "many integrations",
                "webhook", "slack", "email automation", "notification",
                "ai agent", "openai", "chatgpt", "llm"
            ],
        },
        "anti_keywords": [
            "user interface", "frontend", "web app", "mobile app",
            "customer-facing ui", "dashboard ui", "user login ui",
            "simple form", "one step"
        ],
    }),
    ("Make", {
        "display": "Make (Integromat)",
        "description": "Visual automation platform with powerful data transformation and multi-step scenario editor. Best for complex marketing and e-commerce automations.",
        "keywords": {
            "visual_automation": [
                "visual automation", "integromat", "scenario", "multi-step automation",
                "data transform", "data transformation", "formatting", "routing"
            ],
            "marketing_ecommerce": [
                "marketing", "email campaign", "lead nurture", "funnel",
                "e-commerce", "ecommerce", "shopify", "woocommerce",
                "order processing", "invoice", "receipt"
            ],
            "data_operations": [
                "json", "xml", "csv processing", "text parsing",
                "aggregate", "iterator", "array", "loop",
                "conditional logic", "branching", "if-else"
            ],
        },
        "anti_keywords": [
            "self-host", "self host", "self-hosted", "docker",
            "on-premise", "internal tool", "web application",
            "database", "user interface", "mobile"
        ],
    }),
    ("Zapier", {
        "display": "Zapier",
        "description": "Simple trigger-action automation platform with the widest app integration library. Best for straightforward, linear automations between SaaS tools.",
        "keywords": {
            "simple_automation": [
                "zap", "trigger", "simple automation", "one step", "one-step",
                "connect", "integrate", "send to", "copy to",
                "if this then that", "quick automation"
            ],
            "saas_connect": [
                "gmail", "google calendar", "slack", "trello", "asana",
                "hubspot", "salesforce", "mailchimp", "google drive",
                "dropbox", "notion", "clickup"
            ],
            "easy": [
                "easy", "simple", "quick setup", "no technical",
                "no code", "beginner", "non-technical", "first time"
            ],
        },
        "anti_keywords": [
            "complex logic", "multi-step", "multi step", "branching",
            "nested", "database", "self-host", "custom code",
            "enterprise", "high volume", "thousands"
        ],
    }),
])


def score_platform(text_lower, platform_info):
    """Score a platform based on keyword matches and anti-keyword penalties."""
    score = 0
    reasons = []

    for category, keywords in platform_info["keywords"].items():
        matches = []
        for kw in keywords:
            if kw in text_lower:
                matches.append(kw)
        if matches:
            points = len(matches) * 2  # 2 points per keyword match
            score += points
            # Keep the best match per category for the reason
            reasons.append(matches[0])

    # Anti-keyword penalties: each anti-keyword match subtracts 3 points
    anti_penalties = 0
    for akw in platform_info["anti_keywords"]:
        if akw in text_lower:
            anti_penalties += 3

    score = max(0, score - anti_penalties)

    return score, reasons


def recommend(text, format_output="text"):
    """Analyze requirement text and recommend the best platform."""
    text_lower = text.lower()

    # Score all platforms
    results = []
    for name, info in PLATFORMS.items():
        score_val, reasons = score_platform(text_lower, info)
        results.append({
            "platform": info["display"],
            "score": score_val,
            "reasons": reasons,
            "description": info["description"],
        })

    # Sort by score descending
    results.sort(key=lambda r: r["score"], reverse=True)

    top = results[0]
    alternatives = [r for r in results[1:] if r["score"] > 0]

    # Determine confidence
    if top["score"] >= 10:
        confidence = "high"
    elif top["score"] >= 6:
        confidence = "medium"
    elif top["score"] >= 2:
        confidence = "low"
    else:
        confidence = "uncertain"

    # Determine use case category
    use_case = classify_use_case(text_lower)

    if format_output == "json":
        result = {
            "recommendation": top["platform"],
            "confidence": confidence,
            "score": top["score"],
            "reasons": top["reasons"],
            "description": top["description"],
            "use_case": use_case,
            "alternatives": [
                {
                    "platform": alt["platform"],
                    "score": alt["score"],
                    "description": alt["description"],
                }
                for alt in alternatives[:3]
            ],
        }
        return json.dumps(result, indent=2)

    # Text output
    out = []
    out.append("=" * 60)
    out.append("No-Code Platform Recommendation")
    out.append("=" * 60)
    out.append("")
    out.append("Requirement summary: " + use_case)
    out.append("")
    out.append("RECOMMENDED: " + top["platform"])
    out.append("  Confidence: " + confidence.upper())
    out.append("  Score: " + str(top["score"]) + " points")
    out.append("  " + top["description"])
    out.append("")
    out.append("Why this platform:")
    if top["reasons"]:
        for r in top["reasons"]:
            out.append("  - Matched requirement: \"" + r + "\"")
    else:
        out.append("  - No strong keyword matches. This is a best-guess based on general platform fit.")

    if alternatives:
        out.append("")
        out.append("Alternatives to consider:")
        for alt in alternatives[:3]:
            out.append("  - " + alt["platform"] + " (score: " + str(alt["score"]) + ")")
            out.append("    " + alt["description"])

    out.append("")
    if confidence == "uncertain":
        out.append("WARNING: Low confidence. The requirement description is too vague or does not")
        out.append("match any platform's strength. Provide more details about:")
        out.append("  - Who will use this? (internal team vs. external customers)")
        out.append("  - What device? (mobile, desktop, or both)")
        out.append("  - Does it need a database? What kind of data?")
        out.append("  - What integrations are needed?")
    elif confidence == "low":
        out.append("NOTE: Low confidence. Consider providing more detail for a stronger recommendation.")
    out.append("=" * 60)

    return "\n".join(out)


def classify_use_case(text_lower):
    """Classify the general use case category."""
    if any(kw in text_lower for kw in ["mobile", "phone", "field", "ios", "android"]):
        return "mobile application"
    if any(kw in text_lower for kw in ["internal", "admin", "operations", "back office"]):
        return "internal tool / admin panel"
    if any(kw in text_lower for kw in ["automation", "workflow", "integrate", "webhook", "api connect"]):
        return "workflow automation"
    if any(kw in text_lower for kw in ["web app", "saas", "marketplace", "customer-facing"]):
        return "customer-facing web application"
    if any(kw in text_lower for kw in ["spreadsheet", "content", "crm", "project track"]):
        return "data management / content"
    return "general application"


def main():
    parser = argparse.ArgumentParser(
        description="No-Code Platform Recommendation Engine -- suggests the best platform for a given project requirement.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 platform_check.py "I need a mobile app for field workers to log inspections"
  python3 platform_check.py --format json "Build an internal dashboard for our ops team"
  echo "I want to build a marketplace like Airbnb" | python3 platform_check.py -
        """,
    )
    parser.add_argument(
        "requirement",
        nargs="?",
        help="Project requirement description (text). Use '-' to read from stdin.",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args()

    # Get the requirement text
    if args.requirement is None or args.requirement == "-":
        requirement = sys.stdin.read().strip()
    else:
        requirement = args.requirement

    if not requirement:
        print("Error: No requirement provided. Pass text as an argument or pipe via stdin.", file=sys.stderr)
        print("Usage: python3 platform_check.py '<your project description>'", file=sys.stderr)
        sys.exit(1)

    output = recommend(requirement, args.format)
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
