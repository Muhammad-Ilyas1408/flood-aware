"use client";

import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { useMemo } from "react";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";

import type { ShelterResponse, VillageResponse } from "@/types";

const VILLAGE_ICON = L.divIcon({
  className: "",
  html: '<span class="block size-3 rounded-full border-2 border-navy-950 bg-amber-500 shadow"></span>',
  iconSize: [12, 12],
  iconAnchor: [6, 6],
});

const SHELTER_ICON = L.divIcon({
  className: "",
  html: '<span class="block size-3 rounded-full border-2 border-navy-950 bg-risk-normal shadow"></span>',
  iconSize: [12, 12],
  iconAnchor: [6, 6],
});

const DEFAULT_CENTER: [number, number] = [34.75, 72.35];

interface SituationMapProps {
  villages: VillageResponse[];
  shelters: ShelterResponse[];
}

export function SituationMap({ villages, shelters }: SituationMapProps) {
  const center = useMemo<[number, number]>(() => {
    const points = [
      ...villages.map((v) => [v.latitude, v.longitude] as [number, number]),
      ...shelters.map((s) => [s.latitude, s.longitude] as [number, number]),
    ];
    if (points.length === 0) return DEFAULT_CENTER;
    const [latSum, lonSum] = points.reduce(
      ([latAcc, lonAcc], [lat, lon]) => [latAcc + lat, lonAcc + lon],
      [0, 0]
    );
    return [latSum / points.length, lonSum / points.length];
  }, [villages, shelters]);

  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-hidden rounded-xl border border-border">
        <MapContainer
          center={center}
          zoom={10}
          scrollWheelZoom={false}
          style={{ height: 420, width: "100%" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {villages.map((village, index) => (
            <Marker
              key={`village-${index}-${village.name}`}
              position={[village.latitude, village.longitude]}
              icon={VILLAGE_ICON}
            >
              <Popup>
                <strong>{village.name}</strong>
                <br />
                {village.district}
                {village.population !== null &&
                  ` · Population ${village.population.toLocaleString()}`}
              </Popup>
            </Marker>
          ))}
          {shelters.map((shelter, index) => (
            <Marker
              key={`shelter-${index}-${shelter.name}`}
              position={[shelter.latitude, shelter.longitude]}
              icon={SHELTER_ICON}
            >
              <Popup>
                <strong>{shelter.name}</strong>
                <br />
                {shelter.district} · Capacity {shelter.capacity.toLocaleString()}
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>

      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="inline-block size-2.5 rounded-full bg-amber-500" />
          Villages ({villages.length})
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block size-2.5 rounded-full bg-risk-normal" />
          Shelters ({shelters.length})
        </span>
      </div>
    </div>
  );
}
