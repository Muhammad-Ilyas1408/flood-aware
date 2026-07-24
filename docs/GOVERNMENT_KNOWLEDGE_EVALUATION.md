# Government Knowledge Engine Evaluation

## Purpose

This isolated validation layer is the quality gate for Government Knowledge Engine changes. It evaluates retrieval against a maintained benchmark and validates that generated citations correspond to retrieved government evidence. It does not modify the production retrieval pipeline, vector store, prompts, or `KnowledgeTool`.

```text
Benchmark JSON → BenchmarkLoader → EvaluationRunner → MetricsAggregator
                                              ↓
                               EvaluationReportWriter
                               ├── evaluation.json
                               └── evaluation.md
```

## Benchmark format

The default benchmark is `data/knowledge/benchmarks/government_questions.json`.

```json
{
  "questions": [
    {
      "id": "swat-flood-risk",
      "question": "What government evidence describes flood risk in District Swat?",
      "relevant_chunk_ids": ["optional-known-chunk-id"],
      "relevant_documents": ["Disaster_Risk_Mapping_District_Swat.pdf"],
      "expected_citations": [],
      "difficulty": "easy",
      "category": "preparedness",
      "hazard": "flood",
      "agency": "NDMA"
    }
  ]
}
```

Only `id` and `question` are required. Relevance arrays and optional metadata can be omitted, preserving backward compatibility. When present, `difficulty` must be `easy`, `medium`, or `hard`; `category`, `hazard`, and `agency` must be strings.

## CLI usage

The CLI composes the existing production components externally and writes reports without changing the runtime package:

```powershell
uv run python scripts/evaluate_government_knowledge.py
uv run python scripts/evaluate_government_knowledge.py --benchmark data/knowledge/benchmarks/government_questions.json --output-directory data/outputs/evaluation
```

It requires the same configured persistent index and provider credentials as a normal `KnowledgeTool` execution. No external evaluation service or evaluation-specific dependency is used.

## Reading reports

`evaluation.json` is machine-readable; `evaluation.md` is a concise review artifact. Review:

- **Chunk Precision@K / Recall@K** — exact expected chunk IDs only.
- **Document Precision@K / Recall@K** — expected document names only.
- **Hit Rate / MRR** — whether and how early expected evidence was retrieved.
- **Citation Accuracy / Coverage / Missing / Invalid rates** — whether answer citations map to retrieved document, page, and section evidence.

Warnings cause the evaluation to fail, which makes the CLI suitable for CI quality gates.

## Adding questions

Add a new question object to `questions`, supply a stable chunk ID when known or an authoritative document name otherwise, and include expected citations when they are mandatory. Run the CLI and review both generated reports before accepting a RAG change.
