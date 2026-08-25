import type { VariantProps } from "class-variance-authority";
import { Cloud, TriangleAlert } from "lucide-react";

import { Badge, badgeVariants } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { FloodSeverity, VillageConditionResponse } from "@/types";

type BadgeVariant = VariantProps<typeof badgeVariants>["variant"];

/** Mirrors backend/app/village_summary/status_messages.py's severity tiers. */
const SEVERITY_BADGE_VARIANT: Record<FloodSeverity, BadgeVariant> = {
  minor: "risk-normal",
  moderate: "risk-moderate",
  major: "risk-high",
  extreme: "risk-extreme",
};

const SEVERITY_LABEL: Record<FloodSeverity, string> = {
  minor: "Minor",
  moderate: "Moderate",
  major: "Major",
  extreme: "Extreme",
};

interface VillageSnapshotsProps {
  summaries: VillageConditionResponse[];
  unknownVillageNames: string[];
}

export function VillageSnapshots({
  summaries,
  unknownVillageNames,
}: VillageSnapshotsProps) {
  return (
    <div className="flex flex-col gap-3">
      {unknownVillageNames.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Not found in the configured dataset: {unknownVillageNames.join(", ")}
        </p>
      )}
      {summaries.length === 0 ? (
        <Card>
          <CardContent className="py-6 text-center text-sm text-muted-foreground">
            No village snapshots are available right now.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {summaries.map((summary) => (
            <VillageSnapshotCard key={summary.name} summary={summary} />
          ))}
        </div>
      )}
    </div>
  );
}

function VillageSnapshotCard({ summary }: { summary: VillageConditionResponse }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle>{summary.name}</CardTitle>
          {summary.severity ? (
            <Badge variant={SEVERITY_BADGE_VARIANT[summary.severity]}>
              {SEVERITY_LABEL[summary.severity]}
            </Badge>
          ) : (
            <Badge variant="outline">Unknown</Badge>
          )}
        </div>
        <CardDescription>{summary.district}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {summary.weather ? (
          <p className="flex items-center gap-1.5 text-sm text-foreground">
            <Cloud className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            {Math.round(summary.weather.temperature)}°C ·{" "}
            {summary.weather.weather_condition}
          </p>
        ) : (
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <TriangleAlert className="size-4 shrink-0" aria-hidden="true" />
            {summary.weather_unavailable_reason ?? "Weather unavailable"}
          </p>
        )}
        <p className="text-sm text-muted-foreground">{summary.status_message}</p>
        {summary.forecast_stale && (
          <p className="text-xs text-muted-foreground/70">
            Forecast snapshot may be outdated.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
