/**
 * Mirrors backend/app/schemas/datasets.py, backend/app/data/models.py
 * (DatasetMetadata, DatasetStatistics, DatasetBounds), and
 * backend/app/gis/geometry.py (BoundingBox).
 */

import type { BaseResponse, ResponseStatus, SuccessResponse } from "./common";

export interface VillageResponse {
  name: string;
  district: string;
  population: number | null;
  latitude: number;
  longitude: number;
}

export type VillageListResponse = SuccessResponse<VillageResponse[]>;

export interface ShelterResponse {
  name: string;
  district: string;
  capacity: number;
  latitude: number;
  longitude: number;
}

export type ShelterListResponse = SuccessResponse<ShelterResponse[]>;

export interface BoundingBox {
  min_latitude: number;
  min_longitude: number;
  max_latitude: number;
  max_longitude: number;
}

export interface DatasetBounds {
  bounding_box: BoundingBox;
}

/** `coordinate_system` is the raster/vector CRS's EPSG code (e.g. 4326 for WGS84). */
export interface DatasetMetadata {
  name: string;
  description: string;
  version: string;
  source: string;
  created_at: string;
  updated_at: string;
  coordinate_system: number;
  spatial_bounds: DatasetBounds | null;
  tags: string[];
}

export interface DatasetStatistics {
  record_count: number;
}

export interface DatasetSummaryResponse extends BaseResponse {
  status: ResponseStatus;
  metadata: DatasetMetadata;
  statistics: DatasetStatistics;
}

export interface DatasetCatalogResponse extends BaseResponse {
  status: ResponseStatus;
  villages: DatasetSummaryResponse;
  shelters: DatasetSummaryResponse;
}
