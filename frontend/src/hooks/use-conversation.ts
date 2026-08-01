"use client";

import { useEffect, useRef, useState } from "react";

import { ApiError, postConversation } from "@/lib/api-client";
import type { ConversationRequest } from "@/types";

import type { ChatMessageData } from "@/app/agent/chat-message";

type LocationFields = Pick<
  ConversationRequest,
  "village_name" | "district" | "coordinates"
>;

interface UseConversationOptions {
  /** Rotates while a turn is pending -- keep these honest about what's actually happening. */
  statusMessages: readonly string[];
  /** Extra request fields (e.g. village location) layered onto every turn. Omit for none. */
  getLocationFields?: () => LocationFields;
}

export function useConversation({
  statusMessages,
  getLocationFields,
}: UseConversationOptions) {
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [isPending, setIsPending] = useState(false);
  const [statusIndex, setStatusIndex] = useState(0);

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, isPending]);

  useEffect(() => {
    if (!isPending) return;
    const interval = setInterval(() => {
      setStatusIndex((index) => (index + 1) % statusMessages.length);
    }, 1800);
    return () => clearInterval(interval);
  }, [isPending, statusMessages.length]);

  function appendMessage(message: Omit<ChatMessageData, "id">) {
    setMessages((prev) => [...prev, { ...message, id: crypto.randomUUID() }]);
  }

  async function sendConversationTurn(
    requestText: string,
    sid: string | undefined,
    isRetry: boolean
  ) {
    const payload: ConversationRequest = {
      session_id: sid,
      request_text: requestText,
      ...(getLocationFields?.() ?? {}),
    };

    try {
      const response = await postConversation(payload);
      setSessionId(response.session_id);
      appendMessage({
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
      return;
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        setSessionId(undefined);
        if (!isRetry) {
          appendMessage({
            role: "error",
            content:
              "Your session had expired, so I started a fresh one and resent your question.",
          });
          await sendConversationTurn(requestText, undefined, true);
          return;
        }
        appendMessage({
          role: "error",
          content:
            "Couldn't start a new session for that question. Please try sending it again.",
        });
        return;
      }

      if (error instanceof ApiError && error.status === 503) {
        appendMessage({
          role: "error",
          content:
            "The recommendation service is temporarily unavailable. Please try again in a moment.",
        });
        return;
      }

      if (error instanceof ApiError) {
        appendMessage({
          role: "error",
          content:
            error.body?.detail ??
            "Something went wrong processing that request. Please try again.",
        });
        return;
      }

      appendMessage({
        role: "error",
        content:
          "Couldn't reach the Flood-Aware backend. Check your connection and try again.",
      });
    }
  }

  async function sendMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || isPending) return;

    appendMessage({ role: "user", content: trimmed });
    setStatusIndex(0);
    setIsPending(true);
    try {
      await sendConversationTurn(trimmed, sessionId, false);
    } finally {
      setIsPending(false);
    }
  }

  function resetConversation() {
    setSessionId(undefined);
    setMessages([]);
  }

  return {
    messages,
    isPending,
    statusMessage: statusMessages[statusIndex],
    bottomRef,
    sendMessage,
    resetConversation,
  };
}
