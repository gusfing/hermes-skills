#!/usr/bin/env python3
"""
rag_audit.py -- RAG Configuration Auditor
Analyzes a RAG system configuration (JSON or free-text description) and flags
anti-patterns, configuration mistakes, and optimization opportunities.

Part of the "rag-engineer" skill (SkillSeal certified).

Usage:
    python3 rag_audit.py '<json_config>'
    python3 rag_audit.py '<free-text description of RAG setup>'
    python3 rag_audit.py --stdin < config.json
    python3 rag_audit.py --help

JSON config schema (all fields optional):
{
  "chunk_size": 512,
  "chunk_overlap": 50,
  "chunking_strategy": "recursive",
  "embedding_model": "text-embedding-3-small",
  "embedding_dimension": 1536,
  "query_embedding_model": "text-embedding-3-small",
  "similarity_metric": "cosine",
  "vector_db": "qdrant",
  "index_type": "hnsw",
  "top_k": 5,
  "hybrid_search": true,
  "fusion_method": "rrf",
  "reranker": "none",
  "temperature": 0.0,
  "metadata_filtering": "pre",
  "test_dataset": false,
  "test_dataset_size": 0,
  "tenant_isolation": true,
  "cache_enabled": false,
  "prompt_template": "standard",
  "chunk_metadata": true,
  "monitoring_enabled": false,
  "document_types": ["pdf", "markdown"]
}

The script also accepts free-text descriptions and extracts config clues via
keyword matching (e.g., "I split into 256-token chunks with no overlap").
"""

import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Anti-Pattern Detection Rules
# Each rule: (name, description, severity, check_fn)
# Severity: critical, high, medium, low, info
# ---------------------------------------------------------------------------

def _check_chunk_size_too_small(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    size = cfg.get("chunk_size")
    if size is not None and size < 128:
        return (
            "chunk_size_too_small",
            "Chunk size < 128 tokens fragments meaning and destroys context coherence. Minimum recommended: 256 tokens for structured text, 512 for prose.",
            "high",
        )
    return None

def _check_chunk_size_too_large(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    size = cfg.get("chunk_size")
    if size is not None and size > 2048:
        return (
            "chunk_size_too_large",
            "Chunk size > 2048 tokens dilutes relevance and wastes context window. Embedding models also have max token limits (e.g., 8191 for OpenAI, 512 for many open-source models).",
            "medium",
        )
    return None

def _check_chunk_overlap_zero(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    overlap = cfg.get("chunk_overlap")
    if overlap is not None and overlap == 0 and cfg.get("chunking_strategy") != "qa_pair":
        return (
            "chunk_overlap_zero",
            "Zero chunk overlap causes boundary queries to miss context that straddles chunk boundaries. Recommended: 10-20% of chunk size (50-200 tokens for 512-token chunks).",
            "medium",
        )
    return None

def _check_chunk_overlap_excessive(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    overlap = cfg.get("chunk_overlap")
    size = cfg.get("chunk_size")
    if overlap is not None and size is not None and size > 0:
        ratio = overlap / size
        if ratio > 0.5:
            return (
                "chunk_overlap_excessive",
                f"Chunk overlap ({overlap}/{size} = {ratio:.0%}) exceeds 50% of chunk size. High overlap inflates storage cost and causes redundant retrieval results. Recommended: 10-20%.",
                "medium",
            )
    return None

def _check_fixed_size_chunking(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    strategy = cfg.get("chunking_strategy", "").lower()
    if strategy in ("fixed", "fixed_size", "fixed-size", "character"):
        return (
            "fixed_size_chunking",
            "Fixed-size chunking splits text on raw character/token count with no boundary awareness. This breaks sentences and paragraphs. Use recursive, sentence-based, or heading-based chunking instead.",
            "high",
        )
    return None

def _check_mismatched_embedding_models(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    doc_model = cfg.get("embedding_model", "")
    query_model = cfg.get("query_embedding_model", "")
    if doc_model and query_model and doc_model != query_model:
        return (
            "mismatched_embedding_models",
            f"Document embedding model ({doc_model}) differs from query embedding model ({query_model}). Vectors end up in different semantic spaces, destroying retrieval accuracy. Always use the SAME model for both.",
            "critical",
        )
    return None

def _check_dimension_mismatch(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    dim = cfg.get("embedding_dimension")
    model = cfg.get("embedding_model", "").lower()
    known_dims = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
        "all-minilm-l6-v2": 384,
        "all-mpnet-base-v2": 768,
        "e5-large-v2": 1024,
        "bge-large-en-v1.5": 1024,
        "paraphrase-multilingual-minilm-l12-v2": 384,
        "multilingual-e5-large": 1024,
        "embed-multilingual-v3": 1024,
    }
    for key, expected in known_dims.items():
        if key in model and dim is not None and dim != expected:
            return (
                "dimension_mismatch",
                f"Embedding dimension {dim} does not match expected dimension {expected} for model resembling '{model}'. Verify the model's actual output dimension.",
                "medium",
            )
    return None

def _check_no_reranker(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    reranker = cfg.get("reranker", "").lower()
    top_k = cfg.get("top_k", 5)
    if reranker in ("none", "", None) and top_k > 5:
        return (
            "no_reranker_with_high_topk",
            f"Top-K is {top_k} with no reranker configured. High K without reranking introduces noise into generation. Add a cross-encoder reranker (e.g., bge-reranker) and set K=3-5 after reranking.",
            "high",
        )
    return None

def _check_reranker_when_not_needed(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    reranker = cfg.get("reranker", "").lower()
    top_k = cfg.get("top_k", 5)
    if reranker not in ("none", "", None) and top_k <= 3:
        return (
            "reranker_unnecessary",
            f"Reranker is configured but top-K is only {top_k}. Rerankers add cost and latency; they are most valuable when retrieving 10-20 candidates and narrowing to 3-5. Consider increasing pre-rerank K or removing the reranker.",
            "low",
        )
    return None

def _check_high_temperature(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    temp = cfg.get("temperature")
    if temp is not None and temp > 0.5:
        return (
            "high_temperature",
            f"Temperature is {temp}, which is too high for factual RAG. High temperature increases hallucination risk. For factual Q&A, use 0.0-0.3. Reserve higher values for creative generation tasks only.",
            "high",
        )
    return None

def _check_post_retrieval_filtering(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    filtering = cfg.get("metadata_filtering", "").lower()
    if filtering == "post":
        return (
            "post_retrieval_filtering",
            "Metadata filtering is applied AFTER retrieval. This discards potentially relevant results and wastes vector search compute. Filter at query time (pre-retrieval) instead.",
            "high",
        )
    return None

def _check_no_hybrid_search_on_big_db(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    hybrid = cfg.get("hybrid_search")
    db = cfg.get("vector_db", "").lower()
    doc_types = cfg.get("document_types", [])
    if hybrid is False and db in ("qdrant", "weaviate", "elasticsearch"):
        return (
            "hybrid_search_disabled",
            f"Hybrid search is disabled but {db} supports it natively. Hybrid (dense + sparse/BM25) covers both semantic and exact-match queries. Enable it for better coverage, especially with documents containing codes, IDs, or technical terms.",
            "medium",
        )
    return None

def _check_no_test_dataset(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    has_test = cfg.get("test_dataset", False) or cfg.get("test_dataset_size", 0) > 0
    if not has_test:
        return (
            "no_test_dataset",
            "No test dataset configured. Without a ground-truth Q&A set (minimum 50 pairs), you cannot measure whether pipeline changes help or hurt. Create one and run evaluation after every change.",
            "high",
        )
    return None

def _check_small_test_dataset(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    size = cfg.get("test_dataset_size", 0)
    if 0 < size < 30:
        return (
            "small_test_dataset",
            f"Test dataset has only {size} Q&A pairs. Statistical significance requires at least 50. With fewer than 30, metric changes may be noise.",
            "medium",
        )
    return None

def _check_no_tenant_isolation(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    tenant = cfg.get("tenant_isolation")
    if tenant is False:
        return (
            "no_tenant_isolation",
            "Multi-tenant isolation is disabled. In a multi-client setup, this risks data leakage between tenants. Always filter by tenant ID on every query.",
            "critical",
        )
    return None

def _check_no_cache(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    cache = cfg.get("cache_enabled")
    if cache is False:
        return (
            "no_cache",
            "Caching is disabled. Response and embedding caching (Redis) is the single largest cost optimization for RAG. It avoids redundant LLM calls for repeated queries and re-computing embeddings for unchanged documents.",
            "medium",
        )
    return None

def _check_no_monitoring(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    monitoring = cfg.get("monitoring_enabled")
    if monitoring is False:
        return (
            "no_monitoring",
            "Monitoring is disabled. Without observability (Langfuse, Prometheus, structured logs), you cannot detect retrieval degradation, cost spikes, or quality regressions in production.",
            "medium",
        )
    return None

def _check_no_chunk_metadata(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    metadata = cfg.get("chunk_metadata")
    if metadata is False:
        return (
            "no_chunk_metadata",
            "Chunk metadata is not being stored. Without source, page, section, and timestamp metadata, you lose provenance tracking and cannot filter by document attributes.",
            "medium",
        )
    return None

def _check_code_without_code_splitter(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    doc_types = [d.lower() for d in cfg.get("document_types", [])]
    strategy = cfg.get("chunking_strategy", "").lower()
    code_types = {"code", "py", "js", "ts", "go", "java", "rs", "cpp", "c", "rb", "php"}
    if doc_types and any(t in code_types for t in doc_types):
        if strategy not in ("code", "code_aware", "code-aware", "ast"):
            return (
                "code_without_code_splitter",
                f"Source code files detected ({doc_types}) but chunking strategy is '{strategy}', not code-aware. Use an AST-based splitter that respects function, class, and method boundaries.",
                "high",
            )
    return None

def _check_topk_extreme(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    top_k = cfg.get("top_k")
    if top_k is not None:
        if top_k == 1:
            return (
                "topk_one",
                "Top-K is 1. Single-result retrieval is fragile: a near-miss returns irrelevant context. Use at least 3 for factual Q&A.",
                "high",
            )
        if top_k > 50:
            return (
                "topk_excessive",
                f"Top-K is {top_k}. Very high K floods the context window with noise and increases token costs dramatically. Use 3-10 for generation with reranking.",
                "medium",
            )
    return None

def _check_debug_temp_flag(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    """Flag if temperature is exactly 1.0 (common debug default)."""
    temp = cfg.get("temperature")
    if temp is not None and temp == 1.0:
        return (
            "default_temperature",
            "Temperature is 1.0, which is the API default, not an intentional choice. Most RAG systems should use 0.0-0.3 for factual responses.",
            "low",
        )
    return None

def _check_euclidean_distance(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    metric = cfg.get("similarity_metric", "").lower()
    if metric == "euclidean":
        return (
            "euclidean_distance",
            "Euclidean distance is being used as the similarity metric. Cosine similarity is the standard for text embeddings and is generally more robust. Only use Euclidean if you have a specific reason.",
            "low",
        )
    return None

# All rules in priority order (most severe first)
RULES = [
    _check_mismatched_embedding_models,
    _check_no_tenant_isolation,
    _check_chunk_size_too_small,
    _check_fixed_size_chunking,
    _check_no_test_dataset,
    _check_high_temperature,
    _check_code_without_code_splitter,
    _check_post_retrieval_filtering,
    _check_no_reranker,
    _check_topk_extreme,
    _check_chunk_size_too_large,
    _check_chunk_overlap_zero,
    _check_chunk_overlap_excessive,
    _check_dimension_mismatch,
    _check_no_hybrid_search_on_big_db,
    _check_small_test_dataset,
    _check_no_cache,
    _check_no_monitoring,
    _check_no_chunk_metadata,
    _check_reranker_when_not_needed,
    _check_debug_temp_flag,
    _check_euclidean_distance,
]

# ---------------------------------------------------------------------------
# Free-Text Parser
# Extracts config-like values from natural language descriptions
# ---------------------------------------------------------------------------

TEXT_PATTERNS: List[Tuple[str, str, re.Pattern]] = [
    ("chunk_size", r"(?:chunk[_\s]?size|chunks?\s+(?:of|is|are)\s+)(\d+)\s*(?:tokens?|chars?|words?)"),
    ("chunk_overlap", r"(?:overlap|sliding[_\s]?window)\s+(?:of\s+)?(\d+)\s*(?:tokens?|chars?)"),
    ("top_k", r"(?:top[_\s]?[kK]|retrieve\s+(?:top\s+)?|k\s*=\s*)(\d+)"),
    ("temperature", r"temp(?:erature)?\s*(?:=|is|:)\s*(0?\.\d+)"),
    ("embedding_model", r"(?:embedding|embeddings?)\s+(?:model|using)\s+(?:is\s+)?['\"]?([a-zA-Z0-9_\-/.]+)"),
    ("vector_db", r"(?:vector[_\s]?(?:db|database|store)|storing\s+(?:vectors|embeddings)?\s+(?:in|with))\s+['\"]?([a-zA-Z]+)"),
    ("chunking_strategy", r"(?:chunk(?:ing)?[_\s]?(?:strategy|method|approach)|split\s+(?:by|on|using))\s+(?:is\s+)?['\"]?([a-zA-Z_\-\s]+?)(?:\s+(?:chunk|split|with|and|\.|$))"),
    ("hybrid_search", r"(?:hybrid[_\s]?search|keyword\s*\+\s*semantic|dense\s*\+\s*sparse|bm25)"),
    ("reranker", r"(?:rerank|re[_\s]?rank(?:er|ing)?)\s+(?:using|with|is)?\s+['\"]?([a-zA-Z0-9_\-/.]+)"),
    ("similarity_metric", r"(?:similarity|distance)[_\s]?(?:metric|function|measure)\s+(?:is|using)?\s+['\"]?([a-zA-Z]+)"),
    ("fusion_method", r"(?:fusion|combine)\s+(?:method|using)?\s+['\"]?([a-zA-Z]+)"),
    ("index_type", r"(?:index[_\s]?type|using\s+(?:hnsw|ivf|flat))\s+['\"]?([a-zA-Z]+)"),
    ("test_dataset", r"(?:test[_\s]?(?:dataset|set|data)|eval(?:uation)?[_\s]?(?:dataset|set|data)|ground[_\s]?truth)"),
    ("cache_enabled", r"(?:cache|redis|memcached)"),
    ("embedding_dimension", r"(?:embedding[_\s]?dim(?:ension)?|dimension)\s*(?:=|is|of|:)\s*(\d+)"),
    ("metadata_filtering", r"(?:metadata[_\s]?filter|filter\s+(?:by|on)\s+metadata)"),
    ("document_types", r"(?:loading|ingesting|documents?\s+(?:are|include|from))\s+([a-zA-Z,\s]+?)(?:\s+(?:files?|docs?|\.|$))"),
]

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
SEVERITY_LABEL = {"critical": "CRITICAL", "high": "HIGH", "medium": "MEDIUM", "low": "LOW", "info": "INFO"}


def parse_json_config(raw: str) -> Dict[str, Any]:
    """Parse a JSON RAG configuration string."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to find a JSON object in the text
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        raise


def parse_text_config(raw: str) -> Dict[str, Any]:
    """Extract RAG configuration values from a free-text description."""
    config: Dict[str, Any] = {}
    for key, pattern_str in TEXT_PATTERNS:
        if isinstance(pattern_str, str):
            match = re.search(pattern_str, raw, re.IGNORECASE)
            if match:
                value = match.group(1).strip() if match.lastindex else "true"
                # Normalize boolean flags
                if key in ("hybrid_search", "test_dataset", "cache_enabled", "metadata_filtering"):
                    config[key] = True
                elif key == "document_types":
                    config[key] = [t.strip().lower() for t in value.split(",") if t.strip()]
                elif key == "chunking_strategy":
                    config[key] = value.strip().rstrip(".,;: ")
                elif key in ("chunk_size", "chunk_overlap", "top_k", "embedding_dimension"):
                    try:
                        config[key] = int(value)
                    except ValueError:
                        pass
                elif key == "temperature":
                    try:
                        config[key] = float(value)
                    except ValueError:
                        pass
                else:
                    config[key] = value.strip().rstrip(".,;: ")
    return config


def audit(config: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """Run all detection rules against a config dict. Returns list of (name, description, severity)."""
    issues: List[Tuple[str, str, str]] = []
    for rule_fn in RULES:
        result = rule_fn(config)
        if result:
            issues.append(result)
    return issues


def format_report(config: Dict[str, Any], issues: List[Tuple[str, str, str]]) -> str:
    """Format audit results as a readable report."""
    lines = []
    lines.append("=" * 62)
    lines.append("RAG CONFIGURATION AUDIT")
    lines.append("=" * 62)

    # Summary of detected config
    lines.append("")
    lines.append("DETECTED CONFIGURATION:")
    if config:
        for key in sorted(config.keys()):
            lines.append(f"  {key}: {config[key]}")
    else:
        lines.append("  (no configuration values detected)")

    lines.append("")

    if not issues:
        lines.append("RESULT: No anti-patterns detected.")
        lines.append("Your RAG configuration appears healthy based on the provided parameters.")
        lines.append("Note: This audit only checks what was provided. Ensure completeness.")
        return "\n".join(lines)

    # Sort by severity
    issues.sort(key=lambda x: SEVERITY_ORDER.get(x[2], 99))

    # Count by severity
    counts: Dict[str, int] = {}
    for _, _, sev in issues:
        counts[sev] = counts.get(sev, 0) + 1

    lines.append(f"ISSUES FOUND: {len(issues)}")
    for sev in ("critical", "high", "medium", "low", "info"):
        if sev in counts:
            lines.append(f"  {SEVERITY_LABEL[sev]}: {counts[sev]}")

    lines.append("")
    lines.append("-" * 62)

    current_sev = None
    for name, desc, sev in issues:
        if sev != current_sev:
            current_sev = sev
            lines.append(f"\n[{SEVERITY_LABEL[sev]}]")
        lines.append(f"  [{name}]")
        # Word-wrap description at ~58 chars
        words = desc.split()
        line_buf = "    "
        for w in words:
            if len(line_buf) + len(w) + 1 > 60:
                lines.append(line_buf.rstrip())
                line_buf = "    " + w + " "
            else:
                line_buf += w + " "
        if line_buf.strip():
            lines.append(line_buf.rstrip())
        lines.append("")

    # Verdict
    lines.append("-" * 62)
    critical = counts.get("critical", 0)
    high = counts.get("high", 0)
    if critical > 0:
        lines.append("VERDICT: CRITICAL ISSUES -- Fix immediately before production use.")
    elif high >= 3:
        lines.append("VERDICT: SIGNIFICANT ISSUES -- Multiple high-severity problems require attention.")
    elif high > 0:
        lines.append("VERDICT: NEEDS IMPROVEMENT -- Address high-severity issues first.")
    elif counts.get("medium", 0) > 0:
        lines.append("VERDICT: FAIR -- Several optimizations available. Address medium issues.")
    else:
        lines.append("VERDICT: GOOD -- Minor improvements only.")
    lines.append("=" * 62)

    return "\n".join(lines)


def main() -> int:
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print("Usage: python3 rag_audit.py '<json_config_or_text>'")
        print("       python3 rag_audit.py --stdin < config.json")
        print("       python3 rag_audit.py --help")
        print("")
        print("Examples:")
        print("  python3 rag_audit.py '{\"chunk_size\": 100, \"top_k\": 1}'")
        print("  python3 rag_audit.py 'I split documents into 256-token chunks with")
        print("                        no overlap, using Chroma and top_k=3'")
        print("")
        print("Part of the rag-engineer skill. See SKILL.md for full reference.")
        return 0

    raw_input: str
    if args[0] == "--stdin":
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print("Error: No input provided on stdin.", file=sys.stderr)
            return 1
    else:
        raw_input = " ".join(args)

    raw_input = raw_input.strip()
    if not raw_input:
        print("Error: Empty input.", file=sys.stderr)
        return 1

    # Try JSON first, then fall back to text parsing
    config: Dict[str, Any] = {}
    is_json = False
    try:
        config = parse_json_config(raw_input)
        is_json = True
    except (json.JSONDecodeError, ValueError):
        config = parse_text_config(raw_input)

    issues = audit(config)
    report = format_report(config, issues)
    print(report)

    # Exit codes: 0 = ok, 1 = critical/high issues, 2 = medium issues only
    critical_or_high = sum(
        1 for _, _, s in issues if s in ("critical", "high")
    )
    if critical_or_high > 0:
        return 1
    if issues:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
