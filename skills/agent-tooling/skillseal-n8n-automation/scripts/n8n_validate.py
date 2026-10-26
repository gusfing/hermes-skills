#!/usr/bin/env python3
"""
n8n Workflow JSON Validator

Validates an n8n workflow JSON file for structural correctness.
Checks required top-level fields, node schemas, connection integrity,
and common configuration errors.

Usage:
    python3 n8n_validate.py <workflow.json>
    python3 n8n_validate.py <workflow.json> --verbose

Exit codes:
    0 - Workflow is valid
    1 - Validation errors found
    2 - Invalid JSON syntax
    3 - Usage error (missing file, etc.)
"""

import json
import sys
import os
import argparse


# Top-level keys expected in every n8n workflow
REQUIRED_TOP_KEYS = {"name", "nodes", "connections"}

# Keys required on every node
REQUIRED_NODE_KEYS = {"type", "name", "position"}

# Node types that must not have inbound connections (triggers)
TRIGGER_TYPE_SUFFIXES = ("Trigger",)

# Node types that require specific parameters
NODES_REQUIRING_PATH = {
    "n8n-nodes-base.webhook",
    "n8n-nodes-base.webhookTrigger",
}

# Valid response modes for webhook nodes
VALID_RESPONSE_MODES = {"onReceived", "lastNode", "responseNode", "redirect"}

# Valid execution order values
VALID_EXECUTION_ORDERS = {"v0", "v1"}


def load_workflow(filepath):
    """Load and parse a workflow JSON file. Returns (data, errors)."""
    errors = []
    if not os.path.isfile(filepath):
        return None, [f"File not found: {filepath}"]

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return None, [f"Invalid JSON syntax: {e}"]
    except Exception as e:
        return None, [f"Failed to read file: {e}"]

    if not isinstance(data, dict):
        return None, ["Workflow JSON must be a JSON object (dictionary), not an array or scalar."]

    return data, errors


def validate_top_level(data):
    """Check required top-level keys exist. Returns list of error strings."""
    errors = []
    data_keys = set(data.keys())

    for key in REQUIRED_TOP_KEYS:
        if key not in data_keys:
            errors.append(f"Missing required top-level key: '{key}'")

    if "name" in data and not isinstance(data["name"], str):
        errors.append(f"'name' must be a string, got {type(data['name']).__name__}")

    if "nodes" in data and not isinstance(data["nodes"], list):
        errors.append(f"'nodes' must be an array, got {type(data['nodes']).__name__}")

    if "connections" in data and not isinstance(data["connections"], dict):
        errors.append(f"'connections' must be an object, got {type(data['connections']).__name__}")

    if "settings" in data and not isinstance(data.get("settings"), (dict, type(None))):
        errors.append(f"'settings' must be an object, got {type(data['settings']).__name__}")

    if (
        "settings" in data
        and isinstance(data["settings"], dict)
        and "executionOrder" in data["settings"]
        and data["settings"]["executionOrder"] not in VALID_EXECUTION_ORDERS
    ):
        errors.append(
            f"settings.executionOrder must be 'v0' or 'v1', got '{data['settings']['executionOrder']}'"
        )

    return errors


def validate_nodes(nodes):
    """Validate each node in the nodes array. Returns (errors, warnings, node_names)."""
    errors = []
    warnings = []
    node_names = set()

    if not nodes:
        errors.append("Workflow has no nodes. At least one node is required.")
        return errors, warnings, node_names

    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"Node at index {i} is not a JSON object (got {type(node).__name__})")
            continue

        node_name = node.get("name", f"<unnamed node at index {i}>")

        # Check required fields
        for key in REQUIRED_NODE_KEYS:
            if key not in node:
                errors.append(f"Node '{node_name}' missing required field: '{key}'")

        # Type validation
        node_type = node.get("type", "")
        if node_type and not isinstance(node_type, str):
            errors.append(f"Node '{node_name}' has non-string 'type': {node_type}")

        # Name uniqueness
        name = node.get("name", "")
        if name:
            if name in node_names:
                errors.append(f"Duplicate node name: '{name}' (node names must be unique)")
            node_names.add(name)

        # Position validation
        position = node.get("position", [])
        if position:
            if not isinstance(position, list) or len(position) != 2:
                errors.append(
                    f"Node '{node_name}' has invalid 'position': "
                    f"expected [x, y] array, got {position}"
                )
            elif not all(isinstance(v, (int, float)) for v in position):
                errors.append(f"Node '{node_name}' position values must be numbers: {position}")

        # Parameter validation for specific node types
        if node_type in NODES_REQUIRING_PATH:
            params = node.get("parameters", {})
            if not params.get("path"):
                errors.append(
                    f"Webhook node '{node_name}' missing required parameter 'path'"
                )

            response_mode = params.get("responseMode")
            if response_mode and response_mode not in VALID_RESPONSE_MODES:
                warnings.append(
                    f"Webhook node '{node_name}' has unknown responseMode: '{response_mode}'. "
                    f"Valid values: {', '.join(sorted(VALID_RESPONSE_MODES))}"
                )

        # Trigger nodes should hint about credentials if HTTP-based
        if node_type and node_type.endswith(TRIGGER_TYPE_SUFFIXES):
            if node_type.startswith("n8n-nodes-base.http") or node_type.startswith("n8n-nodes-base.rest"):
                credentials = node.get("credentials", {})
                if not credentials:
                    warnings.append(
                        f"Trigger node '{node_name}' has no credentials configured"
                    )

        # Empty node name
        if not name:
            errors.append(f"Node at index {i} has an empty or missing 'name' field")

        # Suspiciously short node name (likely placeholder)
        if name and len(name.strip()) < 3:
            warnings.append(
                f"Node '{node_name}' has very short name ({len(name.strip())} chars); "
                "consider a descriptive name"
            )

    return errors, warnings, node_names


def _extract_targets_from_branch(branch, source_name, output_idx, node_names):
    """Extract and validate target objects from one connection branch (inner list)."""
    errors = []
    warnings = []
    all_targets = set()
    for target in branch:
        if not isinstance(target, dict):
            errors.append(
                f"Connection target for source '{source_name}' output '{output_idx}' "
                f"must be a JSON object, got {type(target).__name__}"
            )
            continue
        target_name = target.get("node", "")
        if not target_name:
            errors.append(
                f"Connection from '{source_name}' output '{output_idx}' "
                f"has a target with no 'node' field"
            )
            continue
        if target_name not in node_names:
            errors.append(
                f"Connection target node '{target_name}' (from '{source_name}') "
                f"does not exist in the nodes array"
            )
        all_targets.add(target_name)
    return errors, warnings, all_targets


def validate_connections(connections, node_names):
    """Validate connection graph integrity. Returns (errors, warnings)."""
    errors = []
    warnings = []

    if not connections and node_names:
        warnings.append(
            "Workflow has nodes but no connections defined. "
            "Each trigger node will execute independently."
        )
        return errors, warnings

    all_targets = set()
    all_sources = set()

    for source_name, outputs in connections.items():
        if source_name not in node_names:
            errors.append(
                f"Connection source node '{source_name}' does not exist in the nodes array"
            )
            continue

        all_sources.add(source_name)

        if not isinstance(outputs, dict):
            errors.append(
                f"Connection output for source '{source_name}' must be a JSON object, "
                f"got {type(outputs).__name__}"
            )
            continue

        for output_idx, branches in outputs.items():
            if not isinstance(branches, list):
                errors.append(
                    f"Connection output '{output_idx}' for source '{source_name}' "
                    f"must be an array, got {type(branches).__name__}"
                )
                continue

            if not branches:
                warnings.append(
                    f"Connection from '{source_name}' output '{output_idx}' has no target nodes"
                )
                continue

            for branch in branches:
                # Each branch is an array of target objects
                if isinstance(branch, list):
                    br_errs, br_warns, br_targets = _extract_targets_from_branch(
                        branch, source_name, output_idx, node_names
                    )
                    errors.extend(br_errs)
                    warnings.extend(br_warns)
                    all_targets.update(br_targets)
                elif isinstance(branch, dict):
                    # Handle edge case: single target dict not wrapped in array
                    br_errs, br_warns, br_targets = _extract_targets_from_branch(
                        [branch], source_name, output_idx, node_names
                    )
                    errors.extend(br_errs)
                    warnings.extend(br_warns)
                    all_targets.update(br_targets)
                else:
                    errors.append(
                        f"Connection from '{source_name}' output '{output_idx}' "
                        f"branch must be an array or object, got {type(branch).__name__}"
                    )

    # Detect isolated nodes (no connections at all)
    connected_nodes = all_sources | all_targets
    isolated = node_names - connected_nodes
    if isolated:
        warnings.append(
            f"Isolated nodes with no connections: {', '.join(sorted(isolated))}"
        )

    # Warn if no trigger nodes detected (no nodes without inbound connections)
    triggers = all_sources - all_targets
    if connections and not triggers:
        warnings.append(
            "No trigger nodes detected — every node has inbound connections. "
            "Workflow may need a trigger (Webhook, Schedule, Manual) to start."
        )

    return errors, warnings


def validate_webhook_nodes(nodes):
    """Additional validation specific to webhook configuration."""
    errors = []
    warnings = []

    webhook_paths = set()
    for node in nodes:
        node_type = node.get("type", "")
        if node_type in NODES_REQUIRING_PATH:
            path = node.get("parameters", {}).get("path", "")
            name = node.get("name", "<unnamed>")
            if path:
                if path in webhook_paths:
                    errors.append(
                        f"Duplicate webhook path '{path}' used by node '{name}'. "
                        "Webhook paths must be unique across a workflow."
                    )
                webhook_paths.add(path)

    return errors, warnings


def print_report(errors, warnings, info, verbose=False):
    """Print a formatted validation report."""
    total_issues = len(errors) + len(warnings)
    border = "=" * 60

    print(border)
    print("  n8n Workflow Validation Report")
    print(border)
    print()

    # Info section
    if info:
        for label, value in info:
            print(f"  {label}: {value}")
        print()

    # Warnings (non-fatal)
    if warnings:
        print(f"  WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"    [!] {w}")
        print()

    # Errors (fatal)
    if errors:
        print(f"  ERRORS ({len(errors)}):")
        for e in errors:
            print(f"    [X] {e}")
        print()

    # Verdict
    print(border)
    if errors:
        print("  VERDICT: INVALID")
        print(f"  {len(errors)} error(s), {len(warnings)} warning(s) found.")
        print("  Fix the errors above before deploying this workflow.")
    elif warnings:
        print("  VERDICT: VALID (with warnings)")
        print(f"  0 errors, {len(warnings)} warning(s) found.")
        print("  Workflow is structurally sound but has noteworthy issues.")
    else:
        print("  VERDICT: VALID")
        print("  No issues found. Workflow structure looks good.")
    print(border)

    return bool(errors)


def main():
    parser = argparse.ArgumentParser(
        description="Validate n8n workflow JSON for structural correctness",
        epilog="Exit codes: 0=valid, 1=invalid, 2=bad JSON, 3=usage error",
    )
    parser.add_argument(
        "workflow_file",
        help="Path to n8n workflow JSON file",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Output additional diagnostic details",
    )
    args = parser.parse_args()

    filepath = args.workflow_file
    verbose = args.verbose

    # Aceita JSON inline OU caminho de arquivo
    if os.path.isfile(filepath):
        # Check file exists and has .json extension
        if not filepath.lower().endswith(".json"):
            print(f"WARNING: File does not have .json extension: {filepath}", file=sys.stderr)
        # Load
        data, load_errors = load_workflow(filepath)
        if load_errors:
            for e in load_errors:
                print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(2 if "Invalid JSON" in load_errors[0] else 3)
    else:
        # Trata o argumento como JSON inline
        try:
            data = json.loads(filepath)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON syntax: {e}", file=sys.stderr)
            sys.exit(2)
        if not isinstance(data, dict):
            print("ERROR: Workflow JSON must be a JSON object (dictionary).", file=sys.stderr)
            sys.exit(2)

    # Validate
    top_errors = validate_top_level(data)
    node_errors, node_warnings, node_names = validate_nodes(data.get("nodes", []))
    conn_errors, conn_warnings = validate_connections(data.get("connections", {}), node_names)
    webhook_errors, webhook_warnings = validate_webhook_nodes(data.get("nodes", []))

    all_errors = top_errors + node_errors + conn_errors + webhook_errors
    all_warnings = node_warnings + conn_warnings + webhook_warnings

    # Gather info
    info = [
        ("Workflow Name", data.get("name", "<unnamed>")),
        ("Node Count", str(len(data.get("nodes", [])))),
        ("Connection Count", str(len(data.get("connections", {})))),
    ]

    if verbose:
        nodes_list = data.get("nodes", [])
        node_types = {}
        for n in nodes_list:
            t = n.get("type", "unknown")
            node_types[t] = node_types.get(t, 0) + 1
        info.append(("Node Types", ", ".join(f"{t}({c})" for t, c in sorted(node_types.items()))))

        triggers = [
            n.get("name", "?")
            for n in nodes_list
            if n.get("type", "").endswith(TRIGGER_TYPE_SUFFIXES)
        ]
        if triggers:
            info.append(("Trigger Nodes", ", ".join(triggers)))

    # Print report
    has_errors = print_report(all_errors, all_warnings, info, verbose=verbose)

    if verbose and all_errors:
        print()
        print("  --- Verbose Node Summary ---")
        for node in data.get("nodes", []):
            name = node.get("name", "?")
            ntype = node.get("type", "?")
            pos = node.get("position", [0, 0])
            params = ", ".join(sorted(node.get("parameters", {}).keys())) if "parameters" in node else "none"
            print(f"    [{ntype}] {name}  @ ({pos[0]}, {pos[1]})  params: {params}")

    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
