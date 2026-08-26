"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowLeft, ClipboardList, Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PageShell } from "@/components/ui/page-shell";
import { Textarea } from "@/components/ui/textarea";
import { NewConversationButton } from "@/components/new-conversation-button";
import { useConversation } from "@/hooks/use-conversation";

import { ChatMessageBubble } from "../agent/chat-message";
import { PendingMessageBubble } from "../agent/pending-message";

const STATUS_MESSAGES = [
  "Reviewing government guidance...",
  "Searching official documents...",
  "Cross-referencing disaster-management plans...",
  "Preparing your answer...",
];

export default function PolicyAdvisorPage() {
  const [inputText, setInputText] = useState("");

  const {
    messages,
    isPending,
    showPending,
    statusMessage,
    bottomRef,
    sendMessage,
    resetConversation,
  } = useConversation({
    statusMessages: STATUS_MESSAGES,
    mode: "policy_advisor",
  });

  async function handleSend() {
    const trimmed = inputText.trim();
    if (!trimmed || isPending) return;
    setInputText("");
    await sendMessage(trimmed);
  }

  return (
    <PageShell className="flex h-[calc(100dvh-3.5rem-1px-10px)] flex-col gap-4 overflow-hidden py-0 sm:h-[calc(100dvh-4rem-1px-10px)] sm:py-0">
      <header className="flex shrink-0 flex-col gap-3 border-b border-border pb-4 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
        <div className="flex flex-col gap-1">
          <Link
            href="/"
            className="flex w-fit items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="size-3" aria-hidden="true" />
            Home
          </Link>
          <h1 className="flex items-center gap-2 font-heading text-2xl font-semibold tracking-tight text-foreground">
            <ClipboardList className="size-6 text-primary" aria-hidden="true" />
            Policy Advisor
          </h1>
          <p className="text-sm text-muted-foreground">
            Ask about government flood policy, disaster-management plans, and
            official guidance -- grounded in real PDMA and NDMP documents.
          </p>
        </div>
        <NewConversationButton
          onClick={resetConversation}
          disabled={messages.length === 0}
        />
      </header>

      <div
        role="log"
        aria-live="polite"
        className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto py-2"
      >
        {messages.length === 0 && (
          <p className="m-auto max-w-sm text-center text-sm text-muted-foreground">
            Ask a question about government flood policy, disaster-management
            plans, or official evacuation guidance.
          </p>
        )}

        {messages.map((message) => (
          <ChatMessageBubble
            key={message.id}
            message={message}
            showRiskBadges={false}
          />
        ))}

        {showPending && <PendingMessageBubble statusMessage={statusMessage} />}

        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void handleSend();
        }}
        className="flex shrink-0 items-end gap-2 border-t border-border pt-4 pb-[env(safe-area-inset-bottom,0px)]"
      >
        <Textarea
          value={inputText}
          onChange={(event) => setInputText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void handleSend();
            }
          }}
          placeholder="Ask about government flood policy, disaster-management plans, or official guidance..."
          disabled={isPending}
          rows={1}
          className="min-h-10 max-h-40 resize-none"
        />
        <Button
          type="submit"
          size="icon"
          disabled={isPending || !inputText.trim()}
          aria-label="Send message"
        >
          <Send className="size-4" aria-hidden="true" />
        </Button>
      </form>
    </PageShell>
  );
}
