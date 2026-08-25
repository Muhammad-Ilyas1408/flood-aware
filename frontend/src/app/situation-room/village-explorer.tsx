"use client";

import { useState } from "react";
import { Compass, Loader2 } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ApiError, postConversation } from "@/lib/api-client";
import type { ConversationRequest } from "@/types";

import { ChatMessageBubble, type ChatMessageData } from "@/app/agent/chat-message";
import { VillageSelector, type VillageSelection } from "@/app/agent/village-selector";

const ASSESSMENT_REQUEST_TEXT =
  "What is the current flood risk for this village, and what actions should residents take?";

function locationFields(
  selection: VillageSelection
): Pick<ConversationRequest, "village_name" | "district" | "coordinates"> {
  if (selection.kind === "village") {
    return {
      village_name: selection.village.name,
      district: selection.village.district,
      coordinates: {
        latitude: selection.village.latitude,
        longitude: selection.village.longitude,
      },
    };
  }
  if (selection.kind === "other") {
    const customName = selection.customName.trim();
    return customName ? { village_name: customName } : {};
  }
  return {};
}

/**
 * Runs the real, existing /conversation endpoint (the same LangGraph-backed
 * agent as the Agent page) for one selected village -- this is deliberately
 * not a second, parallel AI path.
 */
export function VillageExplorer() {
  const [selection, setSelection] = useState<VillageSelection>({ kind: "none" });
  const [isPending, setIsPending] = useState(false);
  const [message, setMessage] = useState<ChatMessageData | null>(null);

  async function handleGetAssessment() {
    if (selection.kind === "none" || isPending) return;
    setIsPending(true);
    setMessage(null);
    try {
      const response = await postConversation({
        request_text: ASSESSMENT_REQUEST_TEXT,
        ...locationFields(selection),
      });
      setMessage({
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.summary,
        decision: {
          risk_level: response.risk_level,
          confidence: response.confidence,
          summary: response.summary,
          actions: response.actions,
          citations: response.citations,
          missing_evidence: response.missing_evidence,
        },
      });
    } catch (error) {
      setMessage({
        id: crypto.randomUUID(),
        role: "error",
        content:
          error instanceof ApiError
            ? (error.body?.detail ??
              "Something went wrong processing that request. Please try again.")
            : "Couldn't reach the Flood-Aware backend. Check your connection and try again.",
      });
    } finally {
      setIsPending(false);
    }
  }

  const hasLocation = selection.kind !== "none";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Compass className="size-4 text-primary" aria-hidden="true" />
          Full village assessment
        </CardTitle>
        <CardDescription>
          Select a village to run the full grounded Flood-Aware Agent -- the
          same evidence-based reasoning as the Agent page.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <VillageSelector
            selection={selection}
            onSelectionChange={setSelection}
            disabled={isPending}
          />
          <Button onClick={handleGetAssessment} disabled={!hasLocation || isPending}>
            {isPending && (
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            )}
            Get full assessment
          </Button>
        </div>

        {message && <ChatMessageBubble message={message} />}
      </CardContent>
    </Card>
  );
}
