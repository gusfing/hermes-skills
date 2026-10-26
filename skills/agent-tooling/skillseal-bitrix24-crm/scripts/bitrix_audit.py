#!/usr/bin/env python3
"""
bitrix_audit.py -- Bitrix24 Pipeline Auditor

Audits a Bitrix24 sales pipeline: counts deals per stage, calculates total
and weighted pipeline value, average days per stage, flags bottlenecks (stages
exceeding configurable time or concentration thresholds), stale deals (no
recent activity), and stage-to-stage conversion rates.

Accepts a JSON string inline or a path to a JSON file.

Usage:
    python3 bitrix_audit.py '{"pipeline_name":"Sales","stages":[...],"deals":[...]}'
    python3 bitrix_audit.py path/to/pipeline_data.json

Options:
    --stale-days N        Max days without activity before flagging (default: 14)
    --bottleneck-days N   Max average days in a stage before flagging (default: 30)
    --bottleneck-pct N    Max percentage of deals in one stage (default: 40)
    --json                Output raw JSON results in addition to the report

Input JSON structure:
    {
      "pipeline_name": "My Pipeline",
      "stages": [
        {"name": "Stage A", "order": 1, "probability": 20},
        ...
      ],
      "deals": [
        {
          "id": "DL-001",
          "title": "Deal Title",
          "stage": "Stage A",
          "amount": 15000.00,
          "entered_stage_date": "2025-06-01",
          "last_activity_date": "2025-06-10",
          "assigned_to": "Sales Rep Name"
        },
        ...
      ]
    }
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(source: str) -> Dict[str, Any]:
    """Load pipeline data from a JSON string or a file path.

    Uses os.path.isfile to distinguish between a file path and inline JSON.
    """
    if os.path.isfile(source):
        with open(source, "r", encoding="utf-8") as fh:
            return json.load(fh)

    try:
        return json.loads(source)
    except json.JSONDecodeError as exc:
        print(
            f"ERROR: '{source[:120]}...' is not a valid file path nor "
            f"parseable JSON.  Details: {exc}"
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def parse_date(raw: str) -> date:
    """Parse a date string, accepting YYYY-MM-DD or ISO-8601 formats."""
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            candidate = raw[:19] if len(raw) >= 19 else raw
            return datetime.strptime(candidate, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date string: {raw!r}")


def days_between(start: date, end: date) -> int:
    """Non-negative day count between two dates."""
    return max(0, (end - start).days)


# ---------------------------------------------------------------------------
# Core audit logic
# ---------------------------------------------------------------------------

def audit_pipeline(
    data: Dict[str, Any],
    stale_days: int = 14,
    bottleneck_days: int = 30,
    bottleneck_pct: float = 40.0,
    reference_date: Optional[date] = None,
) -> Dict[str, Any]:
    """Run the full pipeline audit and return a structured result dict.

    Parameters
    ----------
    data : dict
        Pipeline data with keys "pipeline_name", "stages", "deals".
    stale_days : int
        Deals with no activity longer than this are flagged stale.
    bottleneck_days : int
        Stages whose *average* time exceeds this are flagged as time bottlenecks.
    bottleneck_pct : float
        Stages holding more than this percentage of total deals are flagged
        as concentration bottlenecks.
    reference_date : date or None
        Date to compute elapsed days against.  Defaults to today.

    Returns
    -------
    dict
        Keys: pipeline_name, total_deals, total_pipeline_value,
        weighted_pipeline_value, analysis_date, stage_metrics, bottlenecks,
        stale_deals, stale_threshold_days, conversions.
    """
    pipeline_name = data.get("pipeline_name", "Unnamed Pipeline")
    stages_raw: List[Dict[str, Any]] = data.get("stages", [])
    deals: List[Dict[str, Any]] = data.get("deals", [])

    if not stages_raw:
        print("WARNING: No stages defined in the pipeline data.")
        return {}

    if not deals:
        print("WARNING: No deals provided. Nothing to audit.")
        return {}

    # ------ Build stage lookup -----------------------------------------------
    stage_map: Dict[str, Dict[str, Any]] = {}
    for s in stages_raw:
        stage_map[s["name"]] = {
            "order": s.get("order", 0),
            "probability": s.get("probability", 0),
        }

    ordered_stages = sorted(stages_raw, key=lambda s: s.get("order", 0))

    # ------ Group deals by stage ---------------------------------------------
    stage_deals: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for deal in deals:
        stage_deals[deal.get("stage", "Unknown")].append(deal)

    # ------ Compute metrics --------------------------------------------------
    today = reference_date or date.today()
    total_pipeline_value = 0.0
    weighted_pipeline_value = 0.0
    stale_deals_list: List[Dict[str, Any]] = []
    stage_metrics: Dict[str, Dict[str, Any]] = {}
    bottlenecks: List[Dict[str, Any]] = []

    for stage_name, sd_list in stage_deals.items():
        si = stage_map.get(stage_name, {})
        probability = si.get("probability", 0)

        days_in_stage: List[int] = []
        for deal in sd_list:
            amount = float(deal.get("amount", 0))
            total_pipeline_value += amount
            weighted_pipeline_value += amount * (probability / 100.0)

            # Time in current stage
            entered_raw = deal.get("entered_stage_date")
            if entered_raw:
                entered = parse_date(entered_raw)
                days_in_stage.append(days_between(entered, today))

            # Stale check
            last_act_raw = deal.get("last_activity_date")
            if last_act_raw:
                last_act = parse_date(last_act_raw)
                inactive = days_between(last_act, today)
                if inactive > stale_days:
                    stale_deals_list.append({
                        "deal_id": deal.get("id", "?"),
                        "title": deal.get("title", "?"),
                        "stage": stage_name,
                        "days_inactive": inactive,
                        "assigned_to": deal.get("assigned_to", "?"),
                    })

        avg_days = (
            round(sum(days_in_stage) / len(days_in_stage), 1)
            if days_in_stage
            else 0.0
        )

        stage_amount = sum(float(d.get("amount", 0)) for d in sd_list)

        stage_metrics[stage_name] = {
            "count": len(sd_list),
            "pct_of_pipeline": round(len(sd_list) / len(deals) * 100, 1),
            "avg_days": avg_days,
            "total_amount": round(stage_amount, 2),
        }

    # ------ Bottleneck detection ---------------------------------------------
    # (a) Time-based: average days in stage exceeds threshold
    for name, metrics in stage_metrics.items():
        if metrics["avg_days"] > bottleneck_days:
            bottlenecks.append({
                "type": "time_bottleneck",
                "stage": name,
                "avg_days": metrics["avg_days"],
                "threshold_days": bottleneck_days,
                "detail": (
                    f"Stage '{name}' averages {metrics['avg_days']} days, "
                    f"exceeding the {bottleneck_days}-day threshold."
                ),
            })

    # (b) Concentration-based: percentage of deals in one stage exceeds threshold
    for name, metrics in stage_metrics.items():
        if metrics["pct_of_pipeline"] > bottleneck_pct:
            bottlenecks.append({
                "type": "concentration_bottleneck",
                "stage": name,
                "pct": metrics["pct_of_pipeline"],
                "threshold_pct": bottleneck_pct,
                "detail": (
                    f"Stage '{name}' holds {metrics['pct_of_pipeline']}% of "
                    f"all deals, exceeding the {bottleneck_pct}% threshold."
                ),
            })

    # ------ Stage-to-stage conversion rates -----------------------------------
    conversions: List[Dict[str, Any]] = []
    for i in range(len(ordered_stages) - 1):
        from_name = ordered_stages[i]["name"]
        to_name = ordered_stages[i + 1]["name"]
        from_count = stage_metrics.get(from_name, {}).get("count", 0)
        to_count = stage_metrics.get(to_name, {}).get("count", 0)
        rate = round(to_count / from_count * 100, 1) if from_count > 0 else 0.0
        conversions.append({
            "from": from_name,
            "to": to_name,
            "from_count": from_count,
            "to_count": to_count,
            "conversion_rate": rate,
        })

    # ------ Assemble result ---------------------------------------------------
    return {
        "pipeline_name": pipeline_name,
        "total_deals": len(deals),
        "total_pipeline_value": round(total_pipeline_value, 2),
        "weighted_pipeline_value": round(weighted_pipeline_value, 2),
        "analysis_date": today.isoformat(),
        "stage_metrics": stage_metrics,
        "bottlenecks": bottlenecks,
        "stale_deals": stale_deals_list,
        "stale_threshold_days": stale_days,
        "conversions": conversions,
    }


# ---------------------------------------------------------------------------
# Human-readable report
# ---------------------------------------------------------------------------

def print_report(result: Dict[str, Any]) -> None:
    """Print a formatted audit report to stdout."""
    if not result:
        return

    # ---- Header ----------------------------------------------------------
    print("=" * 64)
    print(f"  BITRIX24 PIPELINE AUDIT: {result['pipeline_name']}")
    print(f"  Analysis Date : {result['analysis_date']}")
    print(f"  Total Deals   : {result['total_deals']}")
    print(f"  Pipeline Value: ${result['total_pipeline_value']:,.2f}")
    print(f"  Weighted Value: ${result['weighted_pipeline_value']:,.2f}")
    print("=" * 64)

    # ---- Stage metrics table ----------------------------------------------
    print()
    print("STAGE METRICS")
    print("-" * 74)
    print(
        f"  {'Stage':<26} {'Cnt':>5} {'%':>6} "
        f"{'Avg Days':>8} {'Amount':>14}"
    )
    print("-" * 74)
    for name, m in sorted(
        result["stage_metrics"].items(),
        key=lambda kv: stage_order(kv[0], result),
    ):
        print(
            f"  {name:<26} {m['count']:>5} {m['pct_of_pipeline']:>5.1f}% "
            f"{m['avg_days']:>7.1f}  ${m['total_amount']:>13,.2f}"
        )
    print("-" * 74)

    # ---- Conversion rates ------------------------------------------------
    if result["conversions"]:
        print()
        print("CONVERSION RATES")
        print("-" * 58)
        print(f"  {'Transition':<32} {'From':>6} {'To':>6} {'Rate':>8}")
        print("-" * 58)
        for c in result["conversions"]:
            label = f"  {c['from']}  ->  {c['to']}"
            print(
                f"{label:<32} {c['from_count']:>6} {c['to_count']:>6} "
                f"{c['conversion_rate']:>7.1f}%"
            )
        print("-" * 58)

    # ---- Bottlenecks -----------------------------------------------------
    if result["bottlenecks"]:
        print()
        print(f"BOTTLENECKS FOUND: {len(result['bottlenecks'])}")
        for b in result["bottlenecks"]:
            print(f"  [{b['type']}] {b['detail']}")
    else:
        print()
        print("BOTTLENECKS: None detected.")

    # ---- Stale deals -----------------------------------------------------
    threshold = result["stale_threshold_days"]
    if result["stale_deals"]:
        print()
        print(
            f"STALE DEALS (no activity in {threshold}+ days): "
            f"{len(result['stale_deals'])}"
        )
        for s in result["stale_deals"]:
            print(
                f"  [{s['deal_id']}] {s['title']}  --  "
                f"Stage: {s['stage']},  "
                f"Inactive: {s['days_inactive']}d,  "
                f"Owner: {s['assigned_to']}"
            )
    else:
        print()
        print(f"STALE DEALS: None (threshold: {threshold} days).")

    print()
    print("=" * 64)


def stage_order(name: str, result: Dict[str, Any]) -> int:
    """Heuristic for sorting stages in report order.

    If a conversions list exists, derive order from there; otherwise
    fall back to alphabetical.
    """
    for i, conv in enumerate(result.get("conversions", [])):
        if conv["from"] == name:
            return i
    return 999


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args(argv: List[str]) -> Tuple[str, int, int, float, bool]:
    """Extract source string and optional flags from command-line args."""
    if len(argv) < 2:
        print(__doc__)
        print("\nERROR: Required argument missing (JSON string or file path).")
        sys.exit(1)

    source = argv[1]
    stale_days = 14
    bottleneck_days = 30
    bottleneck_pct = 40.0
    output_json = False

    i = 2
    while i < len(argv):
        flag = argv[i]
        if flag == "--stale-days" and i + 1 < len(argv):
            stale_days = int(argv[i + 1])
            i += 2
        elif flag == "--bottleneck-days" and i + 1 < len(argv):
            bottleneck_days = int(argv[i + 1])
            i += 2
        elif flag == "--bottleneck-pct" and i + 1 < len(argv):
            bottleneck_pct = float(argv[i + 1])
            i += 2
        elif flag == "--json":
            output_json = True
            i += 1
        else:
            print(f"WARNING: Unknown option: {flag}")
            i += 1

    return source, stale_days, bottleneck_days, bottleneck_pct, output_json


def main() -> None:
    source, stale_days, bottleneck_days, bottleneck_pct, output_json = parse_args(
        sys.argv
    )

    data = load_data(source)
    result = audit_pipeline(
        data,
        stale_days=stale_days,
        bottleneck_days=bottleneck_days,
        bottleneck_pct=bottleneck_pct,
    )

    print_report(result)

    if output_json:
        print("\n--- RAW JSON ---")
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
