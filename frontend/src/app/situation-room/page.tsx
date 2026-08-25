import Link from "next/link";
import { ArrowLeft, Map, TriangleAlert } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageShell } from "@/components/ui/page-shell";
import {
  getDatasetCatalog,
  getShelters,
  getVillageSummaries,
  getVillages,
} from "@/lib/api-client";
import type {
  DatasetSummaryResponse,
  ShelterResponse,
  VillageResponse,
  VillageSummaryListResponse,
} from "@/types";

import { MapLoader } from "./map-loader";
import { VillageExplorer } from "./village-explorer";
import { VillageSnapshots } from "./village-snapshots";

interface SituationData {
  villagesSummary: DatasetSummaryResponse;
  sheltersSummary: DatasetSummaryResponse;
  villages: VillageResponse[];
  shelters: ShelterResponse[];
}

/**
 * Curated sample villages for the snapshot cards. /villages/summary requires
 * explicit names -- it never defaults to "all villages" -- so the sample set
 * lives here rather than being selected by the backend.
 */
const VILLAGE_SNAPSHOT_NAMES = [
  "Bishbanr",
  "Manglawar",
  "Kokarai",
  "Kas",
  "Charbagh",
  "Alamganj",
];

/** Soft-fails on an unreachable backend -- shows a calm fallback card instead of a raw error or a crashed page. */
async function getSituationData(): Promise<SituationData | null> {
  try {
    const [catalog, villagesResponse, sheltersResponse] = await Promise.all([
      getDatasetCatalog({ cache: "no-store" }),
      getVillages({ cache: "no-store" }),
      getShelters({ cache: "no-store" }),
    ]);
    return {
      villagesSummary: catalog.villages,
      sheltersSummary: catalog.shelters,
      villages: villagesResponse.data,
      shelters: sheltersResponse.data,
    };
  } catch {
    return null;
  }
}

/** Soft-fails independently of the rest of the page -- a live-condition hiccup shouldn't hide the map. */
async function getVillageSnapshots(): Promise<VillageSummaryListResponse | null> {
  try {
    return await getVillageSummaries(VILLAGE_SNAPSHOT_NAMES, { cache: "no-store" });
  } catch {
    return null;
  }
}

function DatasetStatCard({
  title,
  summary,
}: {
  title: string;
  summary: DatasetSummaryResponse;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{summary.metadata.name}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <span className="text-sm text-muted-foreground">Records</span>
          <span className="font-heading text-3xl font-semibold text-foreground sm:text-4xl">
            {summary.statistics.record_count.toLocaleString()}
          </span>
        </div>
        <dl className="flex flex-col gap-1 text-xs text-muted-foreground">
          <div className="flex gap-1.5">
            <dt className="font-medium text-foreground/80">Version</dt>
            <dd>{summary.metadata.version}</dd>
          </div>
          <div className="flex gap-1.5">
            <dt className="font-medium text-foreground/80">Source</dt>
            <dd>{summary.metadata.source}</dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}

export default async function SituationRoomPage() {
  const [data, villageSnapshots] = await Promise.all([
    getSituationData(),
    getVillageSnapshots(),
  ]);

  return (
    <PageShell className="flex flex-col gap-8 py-8 sm:py-10">
      <header className="flex flex-col gap-2">
        <Link
          href="/"
          className="flex w-fit items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3" aria-hidden="true" />
          Home
        </Link>
        <h1 className="flex items-center gap-2 font-heading text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
          <Map className="size-7 text-primary" aria-hidden="true" />
          Situation Room
        </h1>
        <p className="max-w-2xl text-muted-foreground">
          A live district overview -- every village and shelter Flood-Aware
          tracks, mapped from real coordinates.
        </p>
      </header>

      {!data ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-10 text-center text-sm text-muted-foreground">
            <TriangleAlert className="size-5" aria-hidden="true" />
            <p>Live village, shelter, and map data is temporarily unavailable.</p>
            <p>Make sure the Flood-Aware backend is running, then refresh this page.</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-6 sm:grid-cols-2">
            <DatasetStatCard title="Villages" summary={data.villagesSummary} />
            <DatasetStatCard title="Shelters" summary={data.sheltersSummary} />
          </div>

          <section className="flex flex-col gap-3">
            <h2 className="text-xl font-semibold text-foreground">
              Village Snapshots
            </h2>
            {villageSnapshots ? (
              <VillageSnapshots
                summaries={villageSnapshots.data}
                unknownVillageNames={villageSnapshots.unknown_village_names}
              />
            ) : (
              <Card>
                <CardContent className="flex flex-col items-center gap-2 py-8 text-center text-sm text-muted-foreground">
                  <TriangleAlert className="size-5" aria-hidden="true" />
                  <p>Live village condition data is temporarily unavailable.</p>
                </CardContent>
              </Card>
            )}
          </section>

          <section className="flex flex-col gap-3">
            <h2 className="text-xl font-semibold text-foreground">Map</h2>
            <MapLoader villages={data.villages} shelters={data.shelters} />
          </section>

          <section className="flex flex-col gap-3">
            <h2 className="text-xl font-semibold text-foreground">
              Full Assessment
            </h2>
            <VillageExplorer />
          </section>
        </>
      )}
    </PageShell>
  );
}
