---
name: skillseal-rag-engineer
description: "Design, build, audit, and optimize RAG (Retrieval-Augmented Generation) systems. Covers the full pipeline: ingestion, chunking, embedding, vector storage, retrieval, reranking, and generation. Includes chunking strategies, chunk sizing, hybrid search, evaluation metrics, and production best practices."
version: 1.0.0
author: Workloop
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [rag, retrieval, embeddings, vector-db, chunking, llm, generation, hybrid-search, reranking]
    category: mlops
    related_skills: [rag-engineering, rag-mastery-referencia, rag-assistente-conhecimento]
---

# RAG Engineer -- Build, Audit, and Optimize RAG Systems

This skill makes an agent act as a RAG engineer: design pipelines, choose chunking strategies, configure vector stores, tune retrieval, and audit existing RAG setups for problems.

## When to Use

Use this skill when the task involves:

- **Designing a RAG pipeline** from scratch (document ingestion to answer generation)
- **Choosing a chunking strategy** for a specific document type (code, prose, tables, legal)
- **Selecting a vector database** based on scale, cost, and latency requirements
- **Auditing an existing RAG config** for anti-patterns and optimization opportunities
- **Evaluating retrieval quality** with metrics (precision, recall, MRR, NDCG, faithfulness)
- **Implementing hybrid search** (semantic + keyword/BM25)
- **Configuring reranking** to improve retrieval precision

Do NOT use for: general LLM prompting, training/fine-tuning models, or non-RAG conversational agents.

## The RAG Pipeline

```
INGESTION -> CHUNKING -> EMBEDDING -> VECTOR STORE -> RETRIEVAL -> RERANK -> GENERATION
```

### 1. Ingestion

Load documents from source formats. Common loaders:

| Source | Tool / Library | Notes |
|---|---|---|
| PDF | pypdf, PyPDFLoader, pdfplumber | Watch for tables and multi-column layouts |
| Word (.docx) | python-docx | Tables may lose structure -- extract carefully |
| Excel (.xlsx) | pandas | Convert rows to text for search; use Text-to-SQL for aggregations |
| Website | BeautifulSoup, RecursiveUrlLoader | Use Playwright/Selenium for JavaScript-heavy pages |
| Markdown | DirectoryLoader, frontmatter parsing | Preserve heading hierarchy |
| Notion | NotionDBLoader, Notion API | Respect block types (toggle, callout, database) |
| GitHub repos | git clone + code splitter | Exclude .git, node_modules, .env, binaries |
| Databases | Custom SQL loader | Extract structured text per row/field |
| Obsidian | DirectoryLoader on vault | Parse frontmatter, respect internal links |

### 2. Chunking

**This is the single highest-leverage decision in RAG quality.** Poor chunking destroys retrieval precision regardless of model or vector store quality.

#### Chunk Size Guidelines

| Document Type | Recommended Size | Overlap | Strategy |
|---|---|---|---|
| Prose / articles / manuals | 512-1024 tokens | 10-20% (50-200 tokens) | Recursive or heading-based |
| Legal contracts | 256-512 tokens | 5-10% | Sentence-based or semantic |
| Code (single file) | 256-512 tokens | 0-5% | Code-aware splitter (by function/class) |
| Code (repository) | 512-1024 tokens per file | 0% | File-level + summary embedding |
| Tables / structured data | Row-level or table-level | 0% | Convert to descriptive text per row |
| FAQ | Q&A pair | 0% | Split by Q&A boundary |
| Chat logs | Turn-level (1-3 exchanges) | 1 turn overlap | Turn-based splitter |
| Long-form books | 1024-2048 tokens | 10% | Recursive with semantic boundaries |

**Critical rule:** Never split mid-sentence or mid-paragraph. Always break on natural boundaries (paragraphs, headings, sentences). Chunking by raw character count with no boundary awareness is the most common and most damaging RAG mistake.

#### Chunking Strategies

| Strategy | How It Works | When to Use | Pitfalls |
|---|---|---|---|
| **Fixed-size** | Split by N tokens/chars with overlap | Simple documents, quick prototypes | Breaks mid-sentence; poor coherence |
| **Recursive** (LangChain default) | Split by paragraph, then sentence, then word | General-purpose prose with clear structure | May split code comments from code |
| **Sliding window** | Fixed-size windows that overlap by K tokens | Chat logs, transcripts | High storage cost (redundancy) |
| **Sentence-based** | Split on sentence boundaries (., !, ?) | Legal, formal text | Long sentences may exceed token limits |
| **Heading-based** (RECOMMENDED for docs) | Split at H1/H2/H3 boundaries | Manuals, documentation, wikis | Fails if documents lack consistent headings |
| **Semantic** | Group sentences by embedding similarity | Long-form content with topic shifts | Computationally expensive; needs threshold tuning |
| **Parent-child** | Small child chunks for retrieval, larger parent for context | Academic papers, long documents | Complex to implement; double storage |
| **Agentic** | LLM decides chunk boundaries | High-value, low-volume content | Expensive (LLM calls); slow |
| **Code-aware** | Split by function, class, method (AST) | Source code | Language-specific; requires AST parser |
| **Token-based** | Split by token count (respects model tokenizer) | When exact token budgets matter | Same boundary issues as fixed-size |

**Proven recommendation (Workloop POC):** Heading-based chunking where each `##` section becomes one chunk, with the heading path prefixed as context: `f"{title}: {body}"`. In testing, 7/7 queries retrieved the exact correct section.

#### Metadata per Chunk

Always attach metadata to every chunk for filtering and provenance:

```json
{
  "source": "manual.pdf",
  "page": 12,
  "section": "Installation",
  "chunk_index": 47,
  "token_count": 384,
  "last_modified": "2025-03-15",
  "tenant_id": "client-42"
}
```

**Rule:** Filter by metadata BEFORE vector search, not after. Metadata filtering post-retrieval discards potentially relevant results and wastes compute.

### 3. Embeddings

Convert text chunks into dense vectors that capture semantic meaning.

#### Model Selection

| Model | Dimension | Max Tokens | Language | Cost |
|---|---|---|---|---|
| OpenAI text-embedding-3-small | 1536 | 8191 | Multilingual (100+) | Paid per token |
| OpenAI text-embedding-3-large | 3072 | 8191 | Multilingual (100+) | Paid per token |
| Cohere embed-multilingual-v3 | 1024 | 512 | Multilingual (100+) | Paid |
| sentence-transformers all-MiniLM-L6-v2 | 384 | 256 | English | Free (local) |
| sentence-transformers all-mpnet-base-v2 | 768 | 384 | English | Free (local) |
| intfloat/e5-large-v2 | 1024 | 512 | English | Free (local) |
| BGE-large-en-v1.5 | 1024 | 512 | English | Free (local) |
| paraphrase-multilingual-MiniLM-L12-v2 | 384 | 128 | 50+ languages | Free (local) |

**Critical: Use the exact same embedding model for both documents and queries.** Mixing models produces vectors in different spaces and destroys retrieval accuracy. If you change models, you must re-index the entire vector store.

**For Portuguese (pt-BR):** `paraphrase-multilingual-MiniLM-L12-v2` or `intfloat/multilingual-e5-large`.

#### Similarity Metrics

| Metric | Formula | Best For | Range |
|---|---|---|---|
| Cosine similarity | dot(A,B) / (||A|| * ||B||) | General text (default) | [-1, 1] |
| Euclidean distance | sqrt(sum((A-B)^2)) | When magnitude matters | [0, inf) |
| Dot product | sum(A * B) | Normalized vectors (faster) | [-1, 1] |

Cosine similarity is the default. Dot product is faster when vectors are already unit-normalized (L2 norm = 1).

### 4. Vector Store

#### Selection Matrix

| Database | Type | Scale | Hosting | Ease | Cost | Hybrid Search | Multi-Tenant |
|---|---|---|---|---|---|---|---|
| Pinecone | SaaS | Billions | Cloud | High | Paid | Yes (dense+sparse) | Namespaces |
| Qdrant | Open Source | Billions | Self-host/Cloud | Medium | Free/Paid | Yes (native) | Collections + payload filters |
| Chroma | Open Source | Millions | Embedded | Very High | Free | No (add-on) | Collections |
| Weaviate | Open Source | Billions | Self-host/Cloud | Medium | Free/Paid | Yes (native BM25 + vector) | Multi-tenancy class |
| Milvus | Open Source | Trillions | Self-host | Low | Free | Yes (Milvus 2.4+) | Partitions |
| pgvector | Extension | 10M-100M | PostgreSQL | High | Free | Via pg_bm25 or tsvector | Schema-level |
| FAISS | Library | Billions | In-process | High | Free | No (manual) | Manual ID prefix |
| Elasticsearch | Search Engine | Billions | Self-host/Cloud | Medium | Free/Paid | Yes (native) | Index/alias pattern |
| LanceDB | Embedded | Millions | In-process | High | Free | Yes (FTS) | Table-level |

#### Quick Decision

- **Zero infra budget + PostgreSQL already in stack** -> pgvector
- **Zero infra budget + new stack** -> Qdrant (self-host) or Chroma (prototype)
- **Zero infrastructure wants** -> Pinecone (fully managed)
- **Need hybrid search built-in** -> Qdrant, Weaviate, or Elasticsearch
- **Billions of vectors** -> Milvus or Pinecone
- **Sensitive data / on-prem** -> Qdrant, Weaviate, Milvus, or pgvector self-hosted
- **Multi-tenant (one instance, many clients)** -> Qdrant (collections + filters)

#### Index Types

| Index | Speed | Memory | Accuracy | Best For |
|---|---|---|---|---|
| HNSW | Fast | High | ~99% | General purpose (default) |
| IVF (Flat/PQ) | Medium | Medium | ~95-99% | Large datasets with memory constraints |
| DiskANN | Medium | Low | ~99% | Billions of vectors on disk |
| Flat (brute force) | Slow | Low | 100% | Small datasets, exact results |

### 5. Retrieval

#### Top-K Selection

| Use Case | Recommended K | Rationale |
|---|---|---|
| Factual Q&A (single answer) | 3-5 | Enough context, minimal noise |
| Summarization | 5-10 | Broader coverage needed |
| Multi-hop reasoning | 10-20 | Needs multiple documents |
| Code generation (context) | 3-7 | Targeted file retrieval |
| Legal / compliance | 5-10 + rerank to 3-5 | Precision critical |

#### Retrieval Strategies

| Strategy | Description | When to Use |
|---|---|---|
| Dense (semantic) | Cosine similarity on embeddings | Core retrieval (always baseline) |
| Sparse (keyword/BM25) | Lexical matching on terms | Product codes, IDs, exact names |
| Hybrid | Combine dense + sparse | General-purpose (best default) |
| MMR (Max Marginal Relevance) | Diversity-aware: penalize similar results | When chunks are highly redundant |
| Multi-query | Generate N query variants, merge results | Ambiguous queries |
| Self-query | LLM extracts metadata filters from query | Structured data with rich metadata |
| Time-weighted | Boost recent documents | News, changelogs, knowledge bases |
| Contextual compression | Post-retrieval: extract relevant sentences only | Long chunks with dilute information |

### 6. Reranking

Reranking is the highest-ROI improvement after fixing chunking. Retrieve more candidates (top 20-50), then use a cross-encoder to score and select the top 3-5.

| Reranker | Type | Speed | Accuracy Gain | Notes |
|---|---|---|---|---|
| Cohere Rerank | API | Fast | High | Paid, easy to use |
| bge-reranker-large | Local | Medium | High | Open source, 1.5B params |
| bge-reranker-v2-m3 | Local | Medium | Very High | Multilingual, best-in-class open |
| ms-marco-MiniLM-L-6-v2 | Local | Fast | Medium | Lightweight, good for prototyping |
| Cross-encoder (all-mpnet) | Local | Slow | Medium | General purpose |
| LLM-as-reranker | API | Slow | Highest | Expensive, use only for critical paths |

**Pipeline:** Retrieve top-20 -> Rerank -> Select top-5 -> Generate answer.

### 7. Generation

#### Prompt Template (Anti-Hallucination)

```
System: You are a precise assistant. Answer ONLY using the provided context.
If the context does not contain the answer, say "I don't have enough information
to answer that question." Do not make up information. Cite the source document
and section when possible.

Context:
{retrieved_chunks}

Question: {user_query}

Answer:
```

#### Generation Settings

| Parameter | Recommended | Rationale |
|---|---|---|
| Temperature | 0.0-0.3 | Factual RAG needs determinism |
| Top-p | 1.0 | Not needed with low temperature |
| Max tokens | 512-2048 | Match expected answer length |
| Presence penalty | 0.0 | Avoid repeating chunks verbatim |
| Frequency penalty | 0.0-0.3 | Minor diversity boost |

#### Citations

Always include source references so users can verify. Format: `[Source: filename, Section X]` or hyperlink when possible. For high-stakes domains (medical, legal, financial), citations are mandatory.

## Hybrid Search

Hybrid search combines dense (semantic/embedding) and sparse (keyword/BM25) retrieval. It is the strongest default retrieval strategy because:

- Dense search handles paraphrasing, synonyms, and conceptual matches
- Sparse search handles exact terms, product codes, IDs, and rare words
- Together they cover each other's blind spots

### Fusion Methods

| Method | Formula | Best For | Notes |
|---|---|---|---|
| RRF (Reciprocal Rank Fusion) | score = sum(1 / (k + rank)) for each ranker, k=60 | General purpose (recommended) | Parameter-free, proven in production |
| Convex combination | alpha * dense_score + (1-alpha) * sparse_score | When scores are normalized | Needs alpha tuning |
| Linear interpolation | w1 * dense + w2 * sparse | Quick setup | Simple, less robust than RRF |

**Default:** RRF with k=60.

## Evaluation Metrics

### Retrieval Metrics

| Metric | What It Measures | Range | How to Compute |
|---|---|---|---|
| Precision@K | Fraction of top-K that are relevant | [0, 1] | relevant_in_top_k / K |
| Recall@K | Fraction of all relevant docs retrieved | [0, 1] | relevant_in_top_k / total_relevant |
| MRR (Mean Reciprocal Rank) | Position of first relevant result | [0, 1] | mean(1 / rank_of_first_relevant) |
| NDCG@K | Rank-aware relevance (position matters) | [0, 1] | DCG / IDCG |
| Hit Rate@K | At least one relevant in top-K | [0, 1] | queries_with_hit / total_queries |
| MAP (Mean Average Precision) | Precision across all recall levels | [0, 1] | mean of average precision per query |

### Generation Metrics

| Metric | What It Measures | How It Works |
|---|---|---|
| Faithfulness | Is the answer grounded in the context? | LLM or NLI model checks each claim against context |
| Answer Relevance | Does the answer address the question? | LLM-as-judge: pairwise comparison |
| Context Relevance | Is the retrieved context on-topic? | LLM checks if context chunks are related to query |
| Groundedness | Are claims supported by sources? | Claim-level verification against retrieved chunks |
| Hallucination Rate | Fraction of unsupported claims | Count claims not in context / total claims |

### Evaluation Frameworks

- **RAGAS** (Recommended): Open source, covers retrieval + generation, LLM-as-judge
- **DeepEval**: Unit-testing framework for LLM outputs, metric library
- **TruLens**: Evaluation + feedback functions, dashboard
- **LangSmith**: LangChain's tracing + evaluation platform
- **ARES**: Automated evaluation with synthetic data generation

**Critical practice:** Always have a ground-truth test set (minimum 50 Q&A pairs). Run evaluation after every pipeline change (chunking, model, prompt) to catch regressions.

## Anti-Patterns (What to Avoid)

1. **Different embedding models for docs and queries** -- vectors end up in different spaces, retrieval is random
2. **Mixed vector dimensions in one collection** -- changing embedding model without re-indexing
3. **Chunking by fixed character count with no boundary awareness** -- breaks sentences and ideas
4. **Too-small chunks (< 128 tokens)** -- insufficient context, fragments meaning
5. **Too-large chunks (> 2048 tokens)** -- dilutes relevance, wastes context window
6. **No metadata on chunks** -- cannot filter by source, date, or tenant
7. **Post-retrieval filtering** -- discard results instead of filtering at query time
8. **Top-K too low (K=1)** -- single-result retrieval misses related context
9. **Top-K too high without reranking** -- noise degrades generation quality
10. **No test dataset** -- cannot measure if changes improve or break retrieval
11. **High temperature for factual RAG** -- LLM hallucinates outside context
12. **No tenant isolation in multi-tenant systems** -- data leakage between clients
13. **Indexing secrets, PII, or credentials** -- vector DBs are not encrypted by default
14. **Ignoring chunk overlap** -- boundary queries hit gaps between chunks
15. **Using the same prompt for all query types** -- factual vs. summarization need different instructions

## Security

| Threat | Description | Mitigation |
|---|---|---|
| Prompt injection via documents | Malicious text in indexed docs manipulates the LLM | Delimit context clearly; separate instructions from data |
| Data leakage (cross-tenant) | One client sees another client's data | Mandatory tenant filter on every query |
| Poisoning | Attacker injects misleading documents into index | Control ingestion sources; validate input |
| PII exposure | Personal data returned in RAG responses | Anonymize before indexing; access control on retrieval |
| Indirect prompt injection | Retrieved chunks contain LLM instructions | System prompt isolation; input sanitization |

## Production Checklist

- [ ] Dockerized deployment (FastAPI + uvicorn)
- [ ] Redis cache: response cache + embedding cache (largest cost savings)
- [ ] Structured JSON logging (timestamp, query, latency, chunks, answer)
- [ ] Monitoring: latency, error rate, cost, retrieval quality
- [ ] Stateless API (scale horizontally)
- [ ] Queue for bulk ingestion (Celery, Redis Queue, or BullMQ)
- [ ] Alert when "I don't know" rate spikes (degraded retrieval)
- [ ] Environment-based config (secrets, endpoints) via env vars
- [ ] Health check endpoint for load balancer
- [ ] Rate limiting per tenant/user
- [ ] Langfuse or similar for LLM observability (traces, cost, quality)

## Common Stack Patterns

### Minimal (prototype)
```
LangChain + Chroma + OpenAI embeddings + Recursive chunking
```

### Production (self-hosted, free)
```
LlamaIndex + Qdrant (Docker) + sentence-transformers + Heading-based chunking +
RRF hybrid search + bge-reranker + Redis cache
```

### Enterprise (managed, scalable)
```
LangChain/LlamaIndex + Pinecone/Weaviate Cloud + Cohere embeddings +
Semantic chunking + Hybrid search + Cohere rerank + Langfuse monitoring
```

### Code-Aware (repository Q&A)
```
Custom loader (AST) + Code-aware chunking + Voyage code embeddings +
pgvector + BM25 hybrid + MMR diversity
```

## Quick Diagnostic: Is Your RAG Broken?

Ask these 5 questions to diagnose a struggling RAG system:

1. **Are chunks coherent?** -- Open a random sample: can a human understand each chunk in isolation? If not, fix chunking.
2. **Are we using the same embedding model everywhere?** -- Check doc and query model match exactly.
3. **What is our recall@5 on the test set?** -- If below 0.6, retrieval is the bottleneck.
4. **What is our faithfulness score?** -- If below 0.8, the LLM is hallucinating outside context.
5. **Do we rerank?** -- If not, adding a bge-reranker is the fastest quality win.

## References

- The audit script `scripts/rag_audit.py` automates config analysis
- See also: `rag-engineering` skill (pt-BR operational guide), `rag-mastery-referencia` skill (ebook reference)
- RAGAS documentation: https://docs.ragas.io
- LangChain RAG guide: https://python.langchain.com/docs/tutorials/rag/
- Qdrant hybrid search: https://qdrant.tech/articles/hybrid-search/
