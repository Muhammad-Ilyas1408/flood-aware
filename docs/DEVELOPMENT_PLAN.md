# Development Plan

This document describes the actual sprint structure followed during development. For the complete, detailed record of what was built, tested, and fixed in each sprint — including real bugs found through live testing and how they were resolved — see `docs/CHANGELOG.md`, which is the authoritative development history.

---

## Methodology

Development followed an iterative, sprint-based approach with a strong emphasis on **live verification over assumed correctness**. A recurring pattern throughout the project: automated unit and integration tests confirmed code-level correctness, but the most significant and subtle bugs were found only through live, adversarial testing against the real running system — and are documented as such, with root causes traced precisely rather than patched around symptomatically.

---

## Sprint Overview

| Sprint | Focus |
|---|---|
| 1–9 | Core backend foundation: repository structure, FastAPI setup, GIS data pipeline, GloFAS forecast ingestion, government knowledge base construction |
| 10 | Village and shelter data services |
| 11 | LLM reasoning and evidence grounding — citation validation, retry-with-feedback correction, specificity enforcement |
| 12 | Multi-tool agent reliability — severity-based routing, graceful tool-failure degradation |
| 13 | Multi-turn conversation and follow-up handling |
| 14 | Production composition root, `POST /conversation` API, real Weather/Forecast integration, GIS performance optimization, RAG retrieval-quality fixes, structural fix for follow-up focus behavior |
| 15 | Production Next.js frontend — full design system, four pages, real navigation, extensive UI/UX polish, root-caused layout fixes |
| 16 | Production deployment — Railway (backend) and Vercel (frontend), CORS production-hardening |

## Ongoing (post-Sprint-16)
- Merging the `frontend-nextjs` branch into `dev`/`main`
- Retiring the Streamlit dashboard as the primary interface (retained as a reference implementation)
- Completing remaining documentation (`API_DOCUMENTATION.md`, `DATA_INVENTORY.md`)
- Final report preparation

---

## Key Engineering Principles Applied Throughout

1. **Grounding over fluency** — a response that honestly declines to speculate is preferred over one that sounds confident but is unsupported by evidence.
2. **Root-cause over patching** — when a fix didn't fully resolve an observed issue, the response was to investigate more deeply (including direct evidence from logs, browser DevTools, and real API traces) rather than attempt a second surface-level patch.
3. **Verify before trusting** — deployment and configuration decisions (data-file inclusion, CORS patterns, third-party library compatibility) were checked against real evidence or authoritative sources before being finalized, not assumed correct.
4. **Real-data testing** — critical fixes were verified against the live, running system with real external API calls, not only mocked test doubles.

---

## Testing Strategy

- **Unit and integration tests** (`backend/tests/`) — fast, deterministic, run on every change, no real external API calls
- **Golden-set evaluation** (`backend/tests/golden/`) — real, live calls against the actual OpenAI API, verifying grounding and reasoning-quality behavior that cannot be meaningfully mocked
- **Live manual verification** — throughout Sprints 14–16, extensive testing directly against the running application (local and, in Sprint 16, production) to catch issues invisible to automated testing alone

Full test results and coverage are recorded per-sprint in `docs/CHANGELOG.md`.