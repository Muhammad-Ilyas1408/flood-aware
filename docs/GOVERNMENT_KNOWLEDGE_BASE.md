# Government Disaster Knowledge Base

## Architecture

Government PDFs are loaded, cleaned, semantically chunked, embedded in batches, and persisted to Chroma by the offline index builder. Runtime retrieval only reads the persistent index.

## Rebuild

Set `OPENAI_API_KEY` and run:

```powershell
python scripts/build_government_index.py
```

The configured PDF directory defaults to `data/knowledge/raw`; add only reviewed authoritative government PDFs there. The builder clears the configured collection before batch-indexing the complete corpus, so it is a deterministic offline rebuild rather than startup work.

## Benchmark Synchronization

After rebuilding the knowledge base, synchronize machine-maintained benchmark retrieval metadata before evaluation:

```powershell
python scripts/build_government_index.py
python scripts/sync_government_benchmark.py
python scripts/evaluate_government_knowledge.py
```

The synchronization utility retrieves each benchmark question through the existing production retriever and refreshes only `relevant_chunk_ids` and `expected_citations` in `data/knowledge/benchmarks/government_questions.json`. It preserves all human-authored fields, including the question, document expectations, difficulty, category, hazard, and agency.

## Metadata

Every chunk carries document name, authority, agency, document type, publication year, page, section, heading, district, river, hazard type, keywords, language, and source path where available. Chroma filters can use scalar metadata fields.

## Retrieval

`GovernmentRetriever` embeds the question, performs Chroma semantic retrieval with optional metadata filters and an optional distance threshold, and returns immutable source chunks. `ContextBuilder` deduplicates passages and preserves citations. `KnowledgeTool` is the public runtime entry point.

## Troubleshooting

If indexing fails, verify the configured PDF directory, explicit embedding API key, write access to the Chroma directory, and valid PDF files. Do not rebuild at application startup.
