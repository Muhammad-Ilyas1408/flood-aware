"use client";

import dynamic from "next/dynamic";

import type { ShelterResponse, VillageResponse } from "@/types";

/** Leaflet touches `window` at module load -- must never be part of the server bundle. */
const SituationMap = dynamic(
  () => import("./situation-map").then((mod) => mod.SituationMap),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[420px] items-center justify-center rounded-xl border border-border bg-card text-sm text-muted-foreground">
        Loading map...
      </div>
    ),
  }
);

interface MapLoaderProps {
  villages: VillageResponse[];
  shelters: ShelterResponse[];
}

export function MapLoader({ villages, shelters }: MapLoaderProps) {
  return <SituationMap villages={villages} shelters={shelters} />;
}
