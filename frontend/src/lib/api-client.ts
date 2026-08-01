/**
 * Typed fetch wrapper for the Flood-Aware backend (see backend/app/api/).
 *
 * Base URL comes from NEXT_PUBLIC_API_BASE_URL (see .env.example) and should
 * include any deployment-specific API prefix — the backend's own
 * `api_prefix` setting defaults to empty, so routes are unprefixed
 * (e.g. `/villages`) unless a given deployment configures otherwise.
 */

import type {
  ConversationRequest,
  ConversationResponse,
  DatasetCatalogResponse,
  ErrorResponse,
  ShelterListResponse,
  VillageListResponse,
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export class ApiError extends Error {
  readonly status: number;
  readonly body: ErrorResponse | null;

  constructor(status: number, body: ErrorResponse | null, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

async function request<TResponse>(
  path: string,
  init?: RequestInit
): Promise<TResponse> {
  if (!API_BASE_URL) {
    throw new Error(
      "NEXT_PUBLIC_API_BASE_URL is not set. Configure it in .env.local to reach the Flood-Aware backend."
    );
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const body = (await response
      .json()
      .catch(() => null)) as ErrorResponse | null;
    throw new ApiError(
      response.status,
      body,
      body?.detail ?? `Request to ${path} failed with status ${response.status}.`
    );
  }

  return (await response.json()) as TResponse;
}

export function getVillages(init?: RequestInit): Promise<VillageListResponse> {
  return request<VillageListResponse>("/villages", init);
}

export function getShelters(init?: RequestInit): Promise<ShelterListResponse> {
  return request<ShelterListResponse>("/shelters", init);
}

export function getDatasetCatalog(
  init?: RequestInit
): Promise<DatasetCatalogResponse> {
  return request<DatasetCatalogResponse>("/datasets/catalog", init);
}

export function postConversation(
  payload: ConversationRequest
): Promise<ConversationResponse> {
  return request<ConversationResponse>("/conversation", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
