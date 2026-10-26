#!/usr/bin/env python3
"""
AI Money Audit Script
Evaluates an AI monetization plan and returns a structured assessment.
Part of the ai-money skill (v1.0.0).

Usage:
    python ai_audit.py '{"plan_name": "...", "category": "...", ...}'
    python ai_audit.py /path/to/plan.json

Output: JSON with score, strengths, risks, recommendations.
"""

import json
import os
import sys
from datetime import datetime


# -- Scoring Dimensions -------------------------------------------------------

DIMENSIONS = {
    "niche_clarity": {
        "label": "Niche Clarity",
        "weight": 0.15,
        "description": "How well-defined and specific is the target niche?",
        "scoring_guide": {
            1: "Extremely vague: 'help everyone' or 'general businesses'",
            4: "Somewhat broad: a sector but no specific segment",
            7: "Well-defined: specific sector with clear pain points",
            10: "Laser-focused: specific segment, clear persona, validated pain point",
        },
    },
    "demand_validation": {
        "label": "Demand Validation",
        "weight": 0.15,
        "description": "Is there evidence that people will pay for this?",
        "scoring_guide": {
            1: "No evidence, pure assumption",
            4: "Anecdotal: 'I think people need this'",
            7: "Some validation: comparable products exist, some search volume",
            10: "Strong validation: existing sales data, high search volume, confirmed pain",
        },
    },
    "value_proposition": {
        "label": "Value Proposition",
        "weight": 0.15,
        "description": "How clear and compelling is the value offered?",
        "scoring_guide": {
            1: "Unclear: cannot articulate what the client gains",
            4: "Generic: 'saves time' without specifics",
            7: "Specific: quantifiable benefit stated",
            10: "Compelling: clear ROI, quantified savings/gains, emotional hook",
        },
    },
    "pricing_strategy": {
        "label": "Pricing Strategy",
        "weight": 0.12,
        "description": "Is the pricing model sound and sustainable?",
        "scoring_guide": {
            1: "No pricing plan or unsustainably low",
            4: "Only hourly, undervaluing AI efficiency",
            7: "Project-based or retainer, reasonable range",
            10: "Value-based pricing, tiered options, clear upsell path",
        },
    },
    "execution_feasibility": {
        "label": "Execution Feasibility",
        "weight": 0.12,
        "description": "Can you realistically deliver this with available resources?",
        "scoring_guide": {
            1: "Requires skills/tools you do not have, no plan to acquire",
            4: "Some capability gaps but no mitigation plan",
            7: "Mostly feasible with minor capability gaps addressed",
            10: "Fully within capability, clear delivery process defined",
        },
    },
    "ai_leverage": {
        "label": "AI Leverage",
        "weight": 0.12,
        "description": "How effectively does the plan use AI tools for leverage?",
        "scoring_guide": {
            1: "No AI usage or trivial automation",
            4: "Uses basic AI (simple text generation) without integration",
            7: "Good AI integration across multiple parts of the workflow",
            10: "Deep AI leverage: automated workflows, AI agents, scale without proportional cost",
        },
    },
    "scalability": {
        "label": "Scalability Potential",
        "weight": 0.10,
        "description": "Can this grow without proportional cost increase?",
        "scoring_guide": {
            1: "Pure time-for-money, 1:1 scaling impossible",
            4: "Some reuse but still heavily time-bound",
            7: "Productized service or digital product with growth path",
            10: "Fully scalable: digital product, automated delivery, recurring revenue",
        },
    },
    "competitive_differentiation": {
        "label": "Competitive Differentiation",
        "weight": 0.09,
        "description": "How different or better is this compared to alternatives?",
        "scoring_guide": {
            1: "Commodity: identical to many existing offers",
            4: "Minor differentiation not clearly communicated",
            7: "Clear differentiator in niche, process, or value",
            10: "Unique angle with strong moat (expertise, data, network, IP)",
        },
    },
}


# -- Risk Patterns -----------------------------------------------------------

RISK_PATTERNS = [
    {
        "condition": lambda d: d.get("niche_clarity", 0) <= 4,
        "risk": "Broad niche: competing against everyone without a clear wedge makes client acquisition difficult and margins low.",
        "severity": "high",
    },
    {
        "condition": lambda d: d.get("demand_validation", 0) <= 4,
        "risk": "Unvalidated demand: building without confirmed willingness to pay risks wasted effort on a product or service nobody buys.",
        "severity": "high",
    },
    {
        "condition": lambda d: d.get("pricing_strategy", 0) <= 5,
        "risk": "Underpricing trap: charging too little attracts low-quality clients, undervalues your work, and leads to burnout. With AI efficiency, hourly billing is especially dangerous.",
        "severity": "high",
    },
    {
        "condition": lambda d: d.get("scalability", 0) <= 3 and d.get("execution_feasibility", 0) >= 5,
        "risk": "Time-ceiling risk: the plan is executable but does not scale. Revenue is capped by your available hours. Consider productizing or adding recurring revenue streams.",
        "severity": "medium",
    },
    {
        "condition": lambda d: d.get("ai_leverage", 0) <= 5,
        "risk": "Low AI leverage: you are not fully exploiting the efficiency gains that give you a competitive advantage. Competitors who automate more will undercut you on price or speed.",
        "severity": "medium",
    },
    {
        "condition": lambda d: d.get("competitive_differentiation", 0) <= 3,
        "risk": "Commodity trap: without clear differentiation, you compete on price alone. This is a race to the bottom, especially with AI lowering barriers to entry.",
        "severity": "medium",
    },
    {
        "condition": lambda d: d.get("execution_feasibility", 0) <= 4 and d.get("ai_leverage", 0) >= 7,
        "risk": "Tool-heavy but skill-light: strong AI tool selection cannot compensate for gaps in domain knowledge or delivery capability. Clients buy outcomes, not tool stacks.",
        "severity": "medium",
    },
    {
        "condition": lambda d: d.get("value_proposition", 0) <= 4,
        "risk": "Weak value communication: even a good service fails to sell if the client cannot see the concrete benefit. Quantify the ROI or risk being dismissed as a 'nice to have.'",
        "severity": "medium",
    },
]


# -- Recommendation Templates ------------------------------------------------

def generate_recommendations(scores, plan_data):
    """Generate contextual recommendations based on scores and plan data."""
    recommendations = []

    category = plan_data.get("category", "").lower()

    if scores.get("niche_clarity", 0) <= 5:
        recommendations.append(
            "Narrow your niche: instead of targeting a broad sector, pick a specific segment "
            "with identifiable pain points (e.g., 'restaurants with delivery operations' instead of 'food businesses'). "
            "A focused niche builds authority faster and makes marketing more efficient."
        )

    if scores.get("demand_validation", 0) <= 5:
        recommendations.append(
            "Validate demand before investing heavily: search for existing products in the space, "
            "check Google Trends and social media conversations, talk to 5-10 potential clients, "
            "or launch a small test (MVP) to confirm willingness to pay."
        )

    if scores.get("pricing_strategy", 0) <= 5:
        recommendations.append(
            "Rethink your pricing model: move away from hourly billing toward project-based or value-based pricing. "
            "Calculate what the client saves or gains from your service and price as a fraction of that value. "
            "Offer 2-3 tiered options (basic/mid/premium) with the middle tier as the anchor."
        )

    if scores.get("value_proposition", 0) <= 5:
        recommendations.append(
            "Sharpen your value proposition: replace generic claims ('saves time') with specific, "
            "quantified outcomes ('reduces response time from 4 hours to 30 seconds, capturing 30% more leads'). "
            "Speak the client's language: frame benefits in terms of revenue gained or costs avoided."
        )

    if scores.get("execution_feasibility", 0) <= 5:
        recommendations.append(
            "Address execution gaps: list the specific skills, tools, or resources you lack and create a plan to acquire them. "
            "Consider partnering with someone who complements your weaknesses, or start with a simpler version of the service "
            "that you can deliver confidently before expanding scope."
        )

    if scores.get("ai_leverage", 0) <= 5:
        recommendations.append(
            "Increase AI leverage: identify repetitive steps in your delivery process and automate them. "
            "Use AI for drafting, summarizing, qualifying, and generating — but always with human review. "
            "Tools like n8n, Zapier, or Make can chain AI calls into automated workflows that run without you."
        )

    if scores.get("scalability", 0) <= 5:
        recommendations.append(
            "Build scalability into the plan: add a digital product component (template, ebook, course) "
            "that generates revenue without consuming your time. Consider a recurring revenue model (retainer, subscription). "
            "Document your processes so they can be delegated later."
        )

    if scores.get("competitive_differentiation", 0) <= 5:
        recommendations.append(
            "Differentiate or die: identify what makes your offer unique — specialized niche knowledge, "
            "a proprietary workflow, faster delivery, better support, bundled value. "
            "Research competitors thoroughly and find the gap they are not filling."
        )

    # Category-specific recommendations
    if category == "service" or category == "consulting":
        recommendations.append(
            "Service-specific: start with a free diagnostic or audit as a low-friction entry point. "
            "Build case studies with measurable results (time saved, revenue gained) as your primary sales tool. "
            "Move toward automation consulting — it commands the highest rates and has recurring revenue potential."
        )
    elif category in ("digital_product", "content"):
        recommendations.append(
            "Product-specific: validate the topic with a small, low-cost version before investing in a full product. "
            "Build an email list with a free lead magnet related to the topic. "
            "Use platforms with built-in traffic (Gumroad, Hotmart, Amazon KDP) before building your own store."
        )
    elif category == "automation":
        recommendations.append(
            "Automation-specific: focus on one niche (restaurants, clinics, real estate) and build a repeatable template. "
            "Offer a maintenance retainer for recurring revenue. Document every integration so you are not the only person "
            "who can maintain the automations."
        )

    if scores.get("demand_validation", 0) >= 7 and scores.get("niche_clarity", 0) >= 7:
        recommendations.append(
            "Strong foundation: your niche and demand signals are solid. Focus on execution speed — "
            "ship a minimum viable version quickly, collect real feedback, and iterate. "
            "Speed to market is a competitive advantage when the fundamentals are right."
        )

    if scores.get("pricing_strategy", 0) >= 7 and scores.get("scalability", 0) <= 4:
        recommendations.append(
            "Pricing is solid but scalability is weak: your pricing model is reasonable, but the plan is capped "
            "by your personal capacity. Add a product or automated delivery layer to break the time-revenue link."
        )

    return recommendations


def identify_strengths(scores, plan_data):
    """Identify top strengths based on highest-scoring dimensions."""
    strengths = []
    sorted_dims = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    for dim_key, score in sorted_dims[:4]:
        if score >= 7:
            dim_info = DIMENSIONS[dim_key]
            strengths.append(
                f"{dim_info['label']} ({score}/10): {dim_info['description']} is well addressed."
            )

    # Add specific strengths based on plan data
    category = plan_data.get("category", "").lower()
    if category == "automation":
        strengths.append(
            "High-value category: automation services command premium pricing and have strong recurring revenue potential. "
            "Businesses pay well to save time."
        )
    elif category in ("digital_product", "content"):
        strengths.append(
            "Scalable foundation: digital products decouple revenue from time. Once created, the product can sell "
            "indefinitely with minimal marginal cost."
        )

    return strengths


def assess_market_fit(scores, plan_data):
    """Generate a market fit assessment based on scores."""
    avg = sum(scores.values()) / len(scores) if scores else 0
    niche = scores.get("niche_clarity", 0)
    demand = scores.get("demand_validation", 0)
    value = scores.get("value_proposition", 0)

    if niche >= 7 and demand >= 7 and value >= 7:
        return (
            "Strong market fit: the niche is well-defined, demand is validated, and the value proposition "
            "is clear. Focus on execution and client acquisition."
        )
    elif niche >= 5 and demand >= 5:
        return (
            "Moderate market fit: the foundations are adequate but need sharpening. "
            "Refine the niche definition or gather more demand evidence before scaling investment."
        )
    else:
        return (
            "Weak market fit: the plan needs significant refinement in niche definition, demand validation, "
            "or value proposition before committing serious resources. Start with discovery and validation."
        )


def suggest_pricing_range(scores, plan_data):
    """Suggest a pricing range based on category and plan characteristics."""
    category = plan_data.get("category", "").lower()
    experience = plan_data.get("experience_level", "beginner").lower()

    multiplier = 1.0
    if experience == "intermediate":
        multiplier = 1.5
    elif experience == "advanced":
        multiplier = 2.0

    if scores.get("value_proposition", 0) >= 8:
        multiplier *= 1.3

    if category in ("service", "consulting", "automation"):
        base = {"low": 80, "mid": 150, "high": 300}
        return {
            "model": "hourly (entry) or per-project (recommended)",
            "hourly_range": f"${int(base['low'] * multiplier)}-${int(base['high'] * multiplier)}/hour",
            "project_range": "$800-$8,000/project depending on scope",
            "monthly_retainer": "$500-$2,000/month for ongoing services",
            "note": "Move from hourly to project/retainer as soon as you have proof of results.",
        }

    elif category in ("digital_product",):
        return {
            "model": "one-time purchase with upsell",
            "entry_price": "$9-$29 (volume-driven lead magnet)",
            "mid_price": "$29-$69 (core product)",
            "premium_price": "$69-$199 (comprehensive/bundle)",
            "note": "Price higher for niche-specific products with clear ROI for the buyer.",
        }

    elif category in ("content",):
        return {
            "model": "ads, sponsorships, affiliates, own products",
            "revenue_streams": [
                "Platform ad revenue (YouTube, blog)",
                "Sponsored content ($100-$2,000+ per placement)",
                "Affiliate commissions (5-30%)",
                "Own digital products (highest margin)",
            ],
            "note": "Build audience first, monetize second. Own products yield the best margins.",
        }

    elif category == "hybrid":
        return {
            "model": "service + product mix",
            "service_component": "Custom work at premium rates (project or retainer)",
            "product_component": "Templates, courses, or tools derived from service work",
            "note": "Services fund the business; products build wealth. Use service revenue to develop products.",
        }

    return {
        "model": "undefined",
        "note": "Define your category more clearly to receive targeted pricing guidance. Common models: hourly, project, retainer, one-time product, subscription.",
    }


def compute_score(plan_data):
    """Main scoring function. Returns a complete assessment dict."""
    scores = {}

    # Score each dimension
    for dim_key, dim_info in DIMENSIONS.items():
        score = plan_data.get(dim_key)
        if score is None:
            # Try to infer score from plan data
            score = infer_dimension_score(dim_key, plan_data)
        if not isinstance(score, (int, float)) or score < 1 or score > 10:
            score = infer_dimension_score(dim_key, plan_data)
        scores[dim_key] = score

    # Compute weighted overall
    weighted_sum = sum(scores[k] * DIMENSIONS[k]["weight"] for k in scores)
    total_weight = sum(DIMENSIONS[k]["weight"] for k in scores)
    overall_score = round((weighted_sum / total_weight) * 10) if total_weight > 0 else 0

    # Generate assessment components
    strengths = identify_strengths(scores, plan_data)
    risks = [
        p["risk"]
        for p in RISK_PATTERNS
        if p["condition"](scores)
    ]
    recommendations = generate_recommendations(scores, plan_data)
    market_fit = assess_market_fit(scores, plan_data)
    pricing = suggest_pricing_range(scores, plan_data)

    # Score tier label
    if overall_score >= 80:
        tier = "Excellent — ready to execute"
    elif overall_score >= 65:
        tier = "Good — refine and launch"
    elif overall_score >= 50:
        tier = "Adequate — needs work before committing resources"
    elif overall_score >= 35:
        tier = "Weak — significant gaps to address"
    else:
        tier = "Poor — rethink the fundamentals"

    return {
        "assessment": {
            "plan_name": plan_data.get("plan_name", "Unnamed Plan"),
            "category": plan_data.get("category", "unspecified"),
            "evaluated_at": datetime.utcnow().isoformat() + "Z",
            "overall_score": overall_score,
            "tier": tier,
            "dimension_scores": {
                DIMENSIONS[k]["label"]: scores[k] for k in scores
            },
        },
        "strengths": strengths,
        "risks": risks,
        "recommendations": recommendations,
        "market_fit_assessment": market_fit,
        "suggested_pricing": pricing,
    }


def infer_dimension_score(dim_key, plan_data):
    """Heuristic inference when explicit scores are not provided."""
    category = plan_data.get("category", "").lower()
    description = plan_data.get("description", "")
    target_niche = plan_data.get("target_niche", "")
    value_prop = plan_data.get("value_proposition", "")
    pricing_model = plan_data.get("pricing_model", "")
    ai_tools = plan_data.get("ai_tools_used", [])
    experience = plan_data.get("experience_level", "beginner")
    monthly_target = plan_data.get("monthly_revenue_target", 0)

    desc_len = len(description) if description else 0
    niche_len = len(target_niche) if target_niche else 0
    vp_len = len(value_prop) if value_prop else 0

    if dim_key == "niche_clarity":
        if niche_len > 80:
            return 9
        elif niche_len > 40:
            return 7
        elif niche_len > 10:
            return 5
        return 3

    if dim_key == "demand_validation":
        evidence = plan_data.get("market_demand_evidence", "")
        competition = plan_data.get("competition_analysis", "")
        if evidence and competition:
            return 8
        elif evidence or competition:
            return 6
        return 4

    if dim_key == "value_proposition":
        if vp_len > 100:
            return 8
        elif vp_len > 50:
            return 6
        elif vp_len > 10:
            return 4
        return 2

    if dim_key == "pricing_strategy":
        pricing_details = plan_data.get("pricing_details", "")
        if "value" in pricing_model.lower() and pricing_details:
            return 9
        elif "project" in pricing_model.lower() or "retainer" in pricing_model.lower():
            return 7
        elif "hourly" in pricing_model.lower():
            return 4
        return 3

    if dim_key == "execution_feasibility":
        if experience == "advanced":
            return 9
        elif experience == "intermediate":
            return 7
        return 5

    if dim_key == "ai_leverage":
        tool_count = len(ai_tools) if isinstance(ai_tools, list) else 0
        if tool_count >= 4:
            return 9
        elif tool_count >= 2:
            return 7
        elif tool_count >= 1:
            return 5
        return 3

    if dim_key == "scalability":
        if category in ("digital_product", "content"):
            return 8
        elif category in ("automation",):
            return 7
        elif category in ("service", "consulting"):
            return 4
        return 5

    if dim_key == "competitive_differentiation":
        if niche_len > 60 and vp_len > 50:
            return 7
        return 5

    return 5


# -- Input Parsing -----------------------------------------------------------

def load_plan(input_arg):
    """Load plan from JSON string or file path."""
    # Check if it is a file path
    if os.path.isfile(input_arg):
        with open(input_arg, "r", encoding="utf-8") as f:
            return json.load(f)

    # Otherwise treat as inline JSON
    try:
        return json.loads(input_arg)
    except json.JSONDecodeError:
        # Try as a file path even if os.path.isfile failed (relative, etc.)
        expanded = os.path.expanduser(input_arg)
        if os.path.isfile(expanded):
            with open(expanded, "r", encoding="utf-8") as f:
                return json.load(f)
        raise ValueError(
            f"Input is not valid JSON and not a readable file: {input_arg}"
        )


# -- CLI Entry Point ----------------------------------------------------------

def main():
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "error": "Usage: ai_audit.py '<json>' OR ai_audit.py <file.json>",
                    "example_inline": 'ai_audit.py \'{"plan_name": "My Plan", "category": "service", ...}\'',
                    "example_file": "ai_audit.py /path/to/plan.json",
                    "expected_fields": {
                        "plan_name": "string (required)",
                        "category": "service | digital_product | content | automation | consulting | hybrid",
                        "target_niche": "string (recommended)",
                        "description": "string (recommended)",
                        "value_proposition": "string (recommended)",
                        "pricing_model": "hourly | project | retainer | subscription | one_time | hybrid",
                        "pricing_details": "string (optional)",
                        "target_clients": "string (optional)",
                        "ai_tools_used": ["list of tool names (optional)"],
                        "delivery_method": "string (optional)",
                        "scalability_path": "string (optional)",
                        "competition_analysis": "string (optional)",
                        "market_demand_evidence": "string (optional)",
                        "monthly_revenue_target": "number (optional)",
                        "experience_level": "beginner | intermediate | advanced",
                        "niche_clarity": "1-10 (optional, auto-inferred)",
                        "demand_validation": "1-10 (optional, auto-inferred)",
                        "value_proposition_score": "1-10 (optional, auto-inferred)",
                        "pricing_strategy": "1-10 (optional, auto-inferred)",
                        "execution_feasibility": "1-10 (optional, auto-inferred)",
                        "ai_leverage": "1-10 (optional, auto-inferred)",
                        "scalability": "1-10 (optional, auto-inferred)",
                        "competitive_differentiation": "1-10 (optional, auto-inferred)",
                    },
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    input_arg = sys.argv[1]

    try:
        plan_data = load_plan(input_arg)
    except (json.JSONDecodeError, ValueError, FileNotFoundError) as e:
        print(json.dumps({"error": str(e)}, indent=2, ensure_ascii=False))
        sys.exit(1)

    result = compute_score(plan_data)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
