/**
 * Mirrors backend/app/schemas/errors.py — the standardized error shape
 * returned by every API failure (see FastAPI exception handlers).
 */

import type { ResponseStatus } from "./common";

export interface ValidationIssue {
  location: (string | number)[];
  message: string;
  error_type: string;
}

export interface ErrorResponse {
  timestamp: string;
  status: ResponseStatus;
  status_code: number;
  detail: string;
  path: string;
  request_id?: string | null;
  errors?: ValidationIssue[] | null;
}
