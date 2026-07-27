# Current Graph Routing Decision Table

This document records the verified behavior of the current LangGraph workflow.
Routing is deterministic and based on flood severity after forecast collection;
it does not inspect query intent.

| Condition after forecast/GIS collection | Nodes executed after forecast | Nodes skipped |
| --- | --- | --- |
| Missing forecast or minor severity | Knowledge, Dataset, Aggregate, Recommendation | GIS, Village, Shelter |
| Moderate severity | GIS, Knowledge, Dataset, Aggregate, Recommendation | Village, Shelter |
| Major or extreme GIS severity | GIS, Village, Shelter, Knowledge, Dataset, Aggregate, Recommendation | None of those nodes |

Weather and Forecast always execute before routing. Knowledge, Dataset,
Aggregate, and Recommendation execute on every routed path. The router reads
only canonical forecast/GIS evidence through `FloodSeverityRoutingPolicy`.

`UserRequest` carries request text, coordinates, village name, district,
province, and scenario request, but no current routing code uses those fields
to choose a tool path. Consequently, forecast-only, shelter, GIS-impact, and
policy/document questions with the same forecast severity follow the same path.
Query-intent-based tool selection is a future design decision and is not part of
the current graph behavior.

When an evidence tool fails, its node records a recoverable graph error, leaves
its owned evidence section empty, and execution continues. The runtime records
that node as failed; later aggregation and recommendation consume the remaining
evidence deterministically.
