/**
 * Mirrors backend/app/schemas/village_summary.py and
 * backend/app/models/enums.py (FloodSeverity).
 */

import type { BaseResponse, ResponseStatus } from "./common";

export type FloodSeverity = "minor" | "moderate" | "major" | "extreme";

export interface WeatherSnapshotResponse {
  temperature: number;
  weather_condition: string;
  weather_description: string;
  humidity: number;
  rainfall: number | null;
  observed_at: string;
}

export interface VillageConditionResponse {
  name: string;
  district: string;
  latitude: number;
  longitude: number;
  weather: WeatherSnapshotResponse | null;
  weather_unavailable_reason: string | null;
  severity: FloodSeverity | null;
  severity_unavailable_reason: string | null;
  forecast_stale: boolean | null;
  status_message: string;
}

export interface VillageSummaryListResponse extends BaseResponse {
  status: ResponseStatus;
  data: VillageConditionResponse[];
  unknown_village_names: string[];
}
