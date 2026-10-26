#!/usr/bin/env python3
"""
Yampi Checkout and Funnel Configuration Validator.

Validates a Yampi store's checkout, sales funnel, cart recovery,
and integration configuration against best practices.

Accepts JSON input in two forms:
  1. Inline JSON string passed as a single argument.
  2. Path to a JSON file passed as a single argument.

Usage:
  python yampi_check.py '{"store": {"name": "My Store"}, ...}'
  python yampi_check.py /path/to/config.json
"""

import json
import sys
import os
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Validation rules and thresholds
# ---------------------------------------------------------------------------

KNOWN_GATEWAYS = {
    "mercadopago", "pagseguro", "paypal", "stone",
    "pagbrasil", "yampi", "pagar.me", "cielo",
}

KNOWN_PAYMENT_METHODS = {
    "credit_card", "debit_card", "pix", "boleto",
}

KNOWN_PIXEL_PROVIDERS = {
    "google_ads", "meta", "facebook", "tiktok", "google_analytics",
}

VALID_WEBHOOK_EVENTS = {
    "order.created", "order.paid", "order.updated",
    "order.cancelled", "cart.abandoned",
    "product.created", "product.updated", "product.deleted",
}

KNOWLEDGE_BASE = {
    "max_upsell_ratio": 0.60,
    "min_recovery_stages": 4,
    "min_gateways": 2,
    "max_abandonment_delay_hours": 3,
    "bump_required": True,
    "fast_checkout_required": True,
    "pix_required": True,
}


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------

Severity = str  # "error", "warning", "info"
Issue = Tuple[Severity, str]


def validate_checkout(config: Dict[str, Any]) -> List[Issue]:
    """Validate transparent checkout configuration."""
    issues: List[Issue] = []
    checkout = config.get("checkout", {})

    if not checkout:
        issues.append(("error", "Missing 'checkout' section in configuration"))
        return issues

    # Transparent checkout
    if checkout.get("type") != "transparent":
        issues.append(
            ("error",
             "Checkout type must be 'transparent' for Yampi. "
             "Redirect-based checkouts lose conversion.")
        )

    # Order bump
    bump = checkout.get("order_bump")
    if bump is None or bump is False:
        issues.append(
            ("warning",
             "Order bump is not configured. This is the highest-ROI feature "
             "(15-30% AOV uplift).")
        )
    elif isinstance(bump, dict):
        if not bump.get("enabled"):
            issues.append(("warning", "Order bump exists but is disabled."))
        if not bump.get("products"):
            issues.append(("warning", "Order bump has no products assigned."))

    # 1-click upsell
    upsell = checkout.get("upsell_1click")
    if not upsell:
        issues.append(
            ("warning",
             "1-click upsell is not configured. Post-purchase offers recover "
             "session momentum.")
        )
    elif isinstance(upsell, dict):
        if not upsell.get("enabled"):
            issues.append(("warning", "1-click upsell exists but is disabled."))
        upsell_ratio = upsell.get("max_order_ratio")
        if upsell_ratio is not None:
            if upsell_ratio > KNOWLEDGE_BASE["max_upsell_ratio"]:
                issues.append(
                    ("warning",
                     f"Upsell ratio {upsell_ratio:.0%} exceeds recommended "
                     f"maximum of {KNOWLEDGE_BASE['max_upsell_ratio']:.0%}. "
                     "Offers above this threshold typically convert poorly.")
                )

    # Fast checkout
    fast = checkout.get("fast_purchase")
    if fast is None or fast is False:
        issues.append(
            ("info",
             "Fast purchase (auto-fill) is not enabled. Returning customers "
             "benefit from reduced form fatigue.")
        )

    # Multi-gateway retry
    gateways = checkout.get("gateways", [])
    gateway_names = set()
    if isinstance(gateways, list):
        for g in gateways:
            if isinstance(g, str):
                gateway_names.add(g.lower())
            elif isinstance(g, dict):
                gateway_names.add(g.get("name", "").lower())

    if len(gateway_names) < KNOWLEDGE_BASE["min_gateways"]:
        issues.append(
            ("error",
             f"Only {len(gateway_names)} payment gateway(s) configured. "
             f"Minimum {KNOWLEDGE_BASE['min_gateways']} required for "
             "multi-gateway retry. A single decline means a lost sale.")
        )

    unknown_gateways = gateway_names - KNOWN_GATEWAYS
    if unknown_gateways:
        issues.append(
            ("info",
             f"Unrecognized gateways: {', '.join(sorted(unknown_gateways))}. "
             "May still be valid; verify in Yampi admin.")
        )

    # Payment methods
    methods = checkout.get("payment_methods", [])
    if isinstance(methods, list):
        method_names = set(
            m.lower() if isinstance(m, str) else m.get("name", "").lower()
            for m in methods
        )
        if KNOWLEDGE_BASE["pix_required"] and "pix" not in method_names:
            issues.append(
                ("warning",
                 "PIX payment method is not enabled. PIX is the highest-"
                 "conversion payment method in Brazil.")
            )
        if "credit_card" not in method_names:
            issues.append(
                ("warning",
                 "Credit card payment is not enabled. Credit cards remain "
                 "the dominant e-commerce payment method in Brazil.")
            )

    return issues


def validate_funnel(config: Dict[str, Any]) -> List[Issue]:
    """Validate sales funnel configuration."""
    issues: List[Issue] = []
    funnel = config.get("funnel", {})

    if not funnel:
        issues.append(("warning", "Missing 'funnel' section in configuration"))
        return issues

    # Pixel tracking
    pixels = funnel.get("pixels", [])
    if isinstance(pixels, list):
        pixel_names = set(
            p.lower() if isinstance(p, str) else p.get("provider", "").lower()
            for p in pixels
        )
        missing = {"google_ads", "meta", "google_analytics"} - pixel_names
        if missing:
            issues.append(
                ("warning",
                 f"Missing pixel integrations: {', '.join(sorted(missing))}. "
                 "Without pixel tracking, retargeting and optimization are "
                 "impossible.")
            )

    # Bump discount anchoring
    bump_discount = funnel.get("bump_discount")
    if not bump_discount and funnel.get("order_bump"):
        issues.append(
            ("info",
             "Order bump exists but no discount anchor configured. "
             "Showing a bundle discount (e.g., 'Add for 30% off') increases "
             "bump conversion.")
        )

    return issues


def validate_cart_recovery(config: Dict[str, Any]) -> List[Issue]:
    """Validate abandoned cart recovery configuration."""
    issues: List[Issue] = []
    recovery = config.get("cart_recovery", {})

    if not recovery:
        issues.append(
            ("warning",
             "Missing 'cart_recovery' section. Abandoned cart recovery is "
             "essential (average ~70% abandonment rate).")
        )
        return issues

    # Native recovery stages
    stages = recovery.get("stages", [])
    if isinstance(stages, list):
        if len(stages) < KNOWLEDGE_BASE["min_recovery_stages"]:
            issues.append(
                ("warning",
                 f"Only {len(stages)} recovery stage(s) configured. "
                 f"Yampi supports up to {KNOWLEDGE_BASE['min_recovery_stages']} "
                 "stages for maximum recovery rate.")
            )

        has_email = any(
            s.get("channel") == "email" for s in stages if isinstance(s, dict)
        )
        has_sms = any(
            s.get("channel") == "sms" for s in stages if isinstance(s, dict)
        )
        has_whatsapp = recovery.get("whatsapp", False) or any(
            s.get("channel") == "whatsapp" for s in stages if isinstance(s, dict)
        )

        if not has_email and not has_sms and not has_whatsapp:
            issues.append(
                ("error",
                 "No recovery channels configured (email, SMS, or WhatsApp).")
            )

        # Stage 1 timing
        if len(stages) > 0 and isinstance(stages[0], dict):
            delay = stages[0].get("delay_hours")
            if delay is not None:
                max_delay = KNOWLEDGE_BASE["max_abandonment_delay_hours"]
                if delay > max_delay:
                    issues.append(
                        ("warning",
                         f"Stage 1 delay is {delay}h, exceeding the "
                         f"recommended maximum of {max_delay}h. "
                         "45% of recoveries happen within 2 hours.")
                    )

        # Coupon escalation
        coupons = [
            s.get("coupon") for s in stages
            if isinstance(s, dict) and s.get("coupon")
        ]
        if len(coupons) < 2 and len(stages) >= 2:
            issues.append(
                ("info",
                 "Fewer than 2 recovery stages have coupon codes. "
                 "Escalating discounts across stages improves recovery rates.")
            )

    # WhatsApp recovery
    whatsapp = recovery.get("whatsapp")
    if not whatsapp:
        issues.append(
            ("warning",
             "WhatsApp recovery is not configured. WhatsApp achieves ~98% "
             "open rates vs ~20% for email. This is the highest-performing "
             "recovery channel in Brazil.")
        )
    elif isinstance(whatsapp, dict):
        provider = whatsapp.get("provider", "").lower()
        valid_providers = {"whapi", "atualizap", "wsupp", "zenvia", "twilio"}
        if provider and provider not in valid_providers:
            issues.append(
                ("info",
                 f"WhatsApp provider '{provider}' not in known providers "
                 f"({', '.join(sorted(valid_providers))}). Verify it supports "
                 "a REST API with HMAC-SHA256 webhook validation.")
            )
        if not whatsapp.get("lgpd_opt_in"):
            issues.append(
                ("error",
                 "LGPD opt-in not confirmed for WhatsApp messaging. "
                 "Sending WhatsApp messages without consent violates "
                 "Brazilian data protection law.")
            )
        if not whatsapp.get("webhook_secret"):
            issues.append(
                ("warning",
                 "No webhook secret configured for WhatsApp integration. "
                 "Always validate Yampi's HMAC-SHA256 signature.")
            )

    return issues


def validate_integrations(config: Dict[str, Any]) -> List[Issue]:
    """Validate integration configuration."""
    issues: List[Issue] = []
    integrations = config.get("integrations", {})

    if not integrations:
        issues.append(("info", "No integrations configured."))
        return issues

    # Webhooks
    webhooks = integrations.get("webhooks", {})
    if webhooks:
        if not webhooks.get("endpoint_url"):
            issues.append(
                ("warning",
                 "Webhooks have no endpoint URL. Yampi webhook events "
                 "cannot be delivered without a configured endpoint.")
            )
        if not webhooks.get("secret"):
            issues.append(
                ("error",
                 "Webhook secret is not configured. Without HMAC-SHA256 "
                 "validation, the webhook endpoint is vulnerable to spoofing.")
            )
        if not webhooks.get("events"):
            issues.append(
                ("warning",
                 "No webhook events selected. At minimum, enable "
                 "order.created, order.paid, and order.cancelled.")
            )
        else:
            unknown = set(webhooks.get("events", [])) - VALID_WEBHOOK_EVENTS
            if unknown:
                issues.append(
                    ("info",
                     f"Unknown webhook events: {', '.join(sorted(unknown))}. "
                     "Verify these exist in Yampi documentation.")
                )

    # Anti-fraud
    antifraud = integrations.get("antifraud")
    if not antifraud:
        issues.append(
            ("info",
             "No anti-fraud integration configured. Consider ClearSale "
             "for transaction risk scoring on high-value orders.")
        )
    elif isinstance(antifraud, dict):
        if not antifraud.get("enabled"):
            issues.append(("info", "Anti-fraud integration exists but is disabled."))

    return issues


def validate_store(config: Dict[str, Any]) -> List[Issue]:
    """Validate store-level settings."""
    issues: List[Issue] = []
    store = config.get("store", {})

    if not store:
        issues.append(("info", "No store information provided."))
        return issues

    # Name
    if not store.get("name"):
        issues.append(
            ("info",
             "Store name not specified. Verify it is configured in Yampi admin.")
        )

    return issues


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def validate(config: Dict[str, Any]) -> Dict[str, Any]:
    """Run all validators and return a structured report."""
    result: Dict[str, Any] = {
        "store": {"name": config.get("store", {}).get("name", "unknown")},
        "errors": [],
        "warnings": [],
        "info": [],
        "summary": {
            "total_issues": 0,
            "errors": 0,
            "warnings": 0,
            "info": 0,
            "valid": True,
        },
    }

    all_validators: List[Tuple[str, callable]] = [
        ("checkout", validate_checkout),
        ("funnel", validate_funnel),
        ("cart_recovery", validate_cart_recovery),
        ("integrations", validate_integrations),
        ("store", validate_store),
    ]

    for section, validator_fn in all_validators:
        issues = validator_fn(config)
        for severity, message in issues:
            entry = f"[{section}] {message}"
            if severity == "error":
                result["errors"].append(entry)
            elif severity == "warning":
                result["warnings"].append(entry)
            else:
                result["info"].append(entry)

    result["summary"]["errors"] = len(result["errors"])
    result["summary"]["warnings"] = len(result["warnings"])
    result["summary"]["info"] = len(result["info"])
    result["summary"]["total_issues"] = (
        result["summary"]["errors"]
        + result["summary"]["warnings"]
        + result["summary"]["info"]
    )
    result["summary"]["valid"] = result["summary"]["errors"] == 0

    return result


# ---------------------------------------------------------------------------
# Input parsing
# ---------------------------------------------------------------------------

def load_config(source: str) -> Dict[str, Any]:
    """Load configuration from an inline JSON string or a file path."""
    # Try as inline JSON first
    try:
        return json.loads(source)
    except json.JSONDecodeError:
        pass

    # Try as file path
    if os.path.isfile(source):
        with open(source, "r", encoding="utf-8") as f:
            return json.load(f)

    # Try as file path with relative resolution
    cwd_path = os.path.join(os.getcwd(), source)
    if os.path.isfile(cwd_path):
        with open(cwd_path, "r", encoding="utf-8") as f:
            return json.load(f)

    raise FileNotFoundError(
        f"Source '{source}' is not valid inline JSON and no file exists at "
        f"that path (also tried '{cwd_path}')."
    )


def format_report(result: Dict[str, Any]) -> str:
    """Format the validation report for terminal output."""
    store_name = result["store"]["name"]
    s = result["summary"]
    lines = [
        "=" * 60,
        f"  Yampi Checkout & Funnel Validation Report",
        f"  Store: {store_name}",
        "=" * 60,
        "",
        f"  Status: {'VALID' if s['valid'] else 'INVALID'}",
        f"  Total issues: {s['total_issues']} "
        f"({s['errors']} errors, {s['warnings']} warnings, {s['info']} info)",
        "",
    ]

    if result["errors"]:
        lines.append("  ERRORS:")
        for e in result["errors"]:
            lines.append(f"    - {e}")
        lines.append("")

    if result["warnings"]:
        lines.append("  WARNINGS:")
        for w in result["warnings"]:
            lines.append(f"    - {w}")
        lines.append("")

    if result["info"]:
        lines.append("  INFO:")
        for i in result["info"]:
            lines.append(f"    - {i}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) != 2:
        print("Usage: yampi_check.py '<json_string>' | yampi_check.py <file.json>")
        print()
        print("Examples:")
        print('  python yampi_check.py \'{"checkout": {"type": "transparent", ...}}\'')
        print("  python yampi_check.py ./my-yampi-config.json")
        sys.exit(1)

    source = sys.argv[1]

    try:
        config = load_config(source)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    result = validate(config)
    print(format_report(result))

    # Exit code reflects validity
    sys.exit(0 if result["summary"]["valid"] else 1)


if __name__ == "__main__":
    main()
