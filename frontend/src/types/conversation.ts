/**
 * Mirrors backend/app/schemas/conversation.py, backend/app/graph/state.py
 * (Coordinate), and the enums backend/app/decision/models.py defines for
 * the public decision surface (RiskLevel, Priority, DecisionConfidence).
 */

import type { BaseResponse, ResponseStatus } from "./common";

export type RiskLevel = "normal" | "low" | "moderate" | "high" | "extreme";
export type Priority = "low" | "medium" | "high" | "critical";
export type DecisionConfidence = "low" | "medium" | "high";
export type ConversationMode = "flood_agent" | "policy_advisor";
export type ConversationResponseType =
  | "flood_decision"
  | "small_talk"
  | "policy_answer";

export interface Coordinate {
  latitude: number;
  longitude: number;
}

export interface ConversationRequest {
  session_id?: string | null;
  request_text: string;
  coordinates?: Coordinate | null;
  village_name?: string | null;
  district?: string | null;
  province?: string | null;
  mode?: ConversationMode;
}

export interface ActionResponse {
  action: string;
  priority: Priority;
}

export interface ConversationResponse extends BaseResponse {
  status: ResponseStatus;
  session_id: string;
  response_type: ConversationResponseType;
  risk_level: RiskLevel | null;
  confidence: DecisionConfidence | null;
  summary: string;
  actions: ActionResponse[];
  citations: string[];
  missing_evidence: string[];
}
