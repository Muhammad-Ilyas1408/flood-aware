# Coding Standards

> Flood-Aware Engineering Standards
>
> Version: 1.0
>
> Status: Active
>
> This document defines the coding conventions and engineering standards for the Flood-Aware project.
>
> Every contributor and AI coding assistant must follow these standards to ensure the codebase remains maintainable, scalable, consistent, and production-ready.

---

# 1. Purpose

The primary objectives of these standards are to:

- Maintain consistent code quality
- Improve readability
- Reduce technical debt
- Simplify debugging
- Encourage modular design
- Support long-term maintainability
- Ensure production-quality implementations

These standards apply to all backend, dashboard, GIS, AI, and utility modules.

---

# 2. Engineering Principles

Every implementation should follow the following principles.

## Production First

Always write production-quality code.

Never write tutorial code.

Never write prototype code.

Never write demonstration code.

---

## Simplicity

Prefer the simplest implementation that correctly solves the problem.

Avoid unnecessary abstraction.

Avoid premature optimization.

---

## Readability

Code is read far more often than it is written.

Prioritize readability over cleverness.

Use descriptive names.

Keep logic easy to follow.

---

## Maintainability

Code should remain understandable six months from now.

Every module should be easy to modify without affecting unrelated components.

---

## Consistency

Maintain consistent:

- formatting
- naming
- architecture
- documentation
- error handling
- logging

throughout the entire project.

---

# 3. Python Standards

Project Python Version

Python 3.11+

Required Features

- Type hints
- Dataclasses where appropriate
- Pattern matching when beneficial
- Modern pathlib usage
- Pydantic v2

Avoid outdated Python patterns.

---

# 4. Project Structure Rules

Never change the project structure without approval.

Each directory has a single responsibility.

Examples:

api/
HTTP endpoints only

services/
Business logic

tools/
External operations

gis/
Spatial processing

rag/
Knowledge retrieval

graph/
LangGraph workflow

models/
Domain models

schemas/
Pydantic schemas

utils/
Reusable helpers

core/
Shared application infrastructure

Never mix responsibilities.

---

# 5. Naming Conventions

## Variables

Use descriptive names.

Good

population_count

forecast_probability

river_level

Bad

x

tmp

value

data1

---

## Functions

Functions should describe actions.

Examples

load_forecast()

calculate_population_exposure()

retrieve_documents()

generate_recommendation()

Avoid generic names.

process()

run()

execute()

handle()

---

## Classes

Use PascalCase.

Example

ForecastService

FloodAgent

GISProcessor

DocumentRetriever

---

## Constants

UPPER_CASE

Example

DEFAULT_TIMEOUT

MAX_UPLOAD_SIZE

CACHE_EXPIRATION_SECONDS

---

## Files

Use snake_case.

Examples

health.py

forecast_service.py

population_analysis.py

Avoid CamelCase filenames.

---

# 6. Function Design

Each function should have one responsibility.

Prefer

Small functions

instead of

Large multi-purpose functions.

Target

10–40 lines

when practical.

If a function becomes difficult to understand, split it.

---

# 7. Type Hints

All public functions must include type hints.

Example

def load_forecast(date: datetime) -> Forecast:
    ...

Avoid untyped public interfaces.

---

# 8. Docstrings

Every public:

- function
- class
- module

should contain meaningful docstrings.

Explain:

Purpose

Parameters

Returns

Raises (when applicable)

Avoid obvious comments.

Bad

Returns value.

Good

Returns the processed flood forecast for the requested date.

---

# 9. Imports

Imports should be grouped.

Standard Library

Third-party

Project imports

Example

import logging
from pathlib import Path

from fastapi import APIRouter

from backend.app.services.forecast_service import ForecastService

Avoid wildcard imports.

Never use

from module import *

---

# 10. Logging Standards

Never use print().

Always use the logging module.

Log:

Application startup

Shutdown

Warnings

Errors

External API failures

Unexpected exceptions

GIS processing

LLM requests

Document retrieval

Avoid excessive logging.

Sensitive information must never be logged.

---

# 11. Error Handling

Never silently ignore exceptions.

Bad

except:
    pass

Good

except HTTPError as exc:
    logger.exception("Forecast API request failed.")
    raise ForecastServiceError(...) from exc

Always provide meaningful error messages.

---

# 12. Configuration

Never hardcode:

API keys

Model names

URLs

File paths

Timeouts

Thresholds

Cache durations

Everything configurable belongs in settings.py.

---

# 13. FastAPI Standards

API routes should remain thin.

Routes perform:

Validation

Authentication (future)

Response serialization

Delegation

Business logic belongs inside services.

Never inside routes.

---

# 14. Pydantic Standards

All API input and output should use Pydantic models.

Avoid dictionaries whenever a schema exists.

Validation belongs inside schemas.

---

# 15. LangGraph Standards

Maintain a single orchestration graph.

Each node should perform one responsibility.

Nodes should remain deterministic whenever possible.

Avoid embedding business logic directly into graph construction.

---

# 16. GIS Standards

Always validate coordinate reference systems.

Avoid duplicated spatial calculations.

Prefer vectorized GeoPandas operations.

Document CRS assumptions.

Never hardcode spatial file locations.

---

# 17. RAG Standards

Documents should be:

Loaded

Chunked

Embedded

Cached

Retrieved

Never re-embed unchanged documents.

Ground responses using retrieved context.

Return citations whenever possible.

---

# 18. Performance Guidelines

Avoid duplicate computation.

Cache expensive operations.

Prefer lazy loading for large datasets.

Minimize unnecessary API calls.

Reuse initialized models.

---

# 19. Security Standards

Never commit:

API keys

Secrets

Passwords

Tokens

Certificates

Never trust user input.

Validate uploaded files.

Sanitize filenames.

Limit upload size.

---

# 20. Testing Standards

Every important module should eventually include tests.

Testing priorities

Configuration

API endpoints

GIS calculations

Population estimation

RAG retrieval

Decision workflow

Regression testing should be added for bug fixes.

---

# 21. Git Standards

Development branch

dev

Production branch

main

Commit frequently.

Each commit should represent one logical change.

Examples

Add application configuration

Implement health endpoint

Add GIS utilities

Avoid commits such as

fix

update

changes

stuff

Commit messages should use the imperative mood.

Examples

Add health endpoint

Implement logging configuration

Configure application settings

---

# 22. Formatting

The project uses

Black

for formatting.

Ruff

for linting.

MyPy

for static type checking.

Do not manually format against these tools.

---

# 23. Code Review Checklist

Before considering a module complete, verify:

✓ Architecture respected

✓ Single responsibility

✓ Type hints added

✓ Logging included

✓ Error handling implemented

✓ Configuration externalized

✓ No duplicated logic

✓ No hardcoded values

✓ Public interfaces documented

✓ Imports organized

✓ Clean formatting

✓ Tests added when applicable

---

# 24. AI Assistant Requirements

When an AI coding assistant generates code, it must:

- Read AI_CONTEXT.md before implementation.
- Follow the project architecture exactly.
- Modify only the requested files.
- Avoid introducing unrelated changes.
- Explain design decisions briefly.
- Produce complete implementations.
- Stop after completing the requested task.

AI assistants must never redesign the architecture or invent new project requirements.

---

# 25. Definition of Done

A task is considered complete only when:

- It satisfies functional requirements.
- It follows the project architecture.
- It complies with these coding standards.
- It includes appropriate logging.
- It includes proper validation.
- It handles expected errors.
- It passes formatting and linting checks.
- It is ready for review and integration.

Code that works but violates these standards is **not** considered complete.