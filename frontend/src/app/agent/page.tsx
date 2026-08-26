"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowLeft, Compass, Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PageShell } from "@/components/ui/page-shell";
import { Textarea } from "@/components/ui/textarea";
import { NewConversationButton } from "@/components/new-conversation-button";
import { useConversation } from "@/hooks/use-conversation";
import type { ConversationRequest } from "@/types";

import { ChatMessageBubble } from "./chat-message";
import { PendingMessageBubble } from "./pending-message";
import { VillageSelector, type VillageSelection } from "./village-selector";

const STATUS_MESSAGES = [
  "Analyzing flood zone data...",
  "Reviewing weather and forecast data...",
  "Cross-checking village and shelter records...",
  "Preparing your recommendation...",
];

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

// "Other / not listed" with a blank name resolves to no location at all --
// treat it the same as no selection so a flood question can't be submitted
// without something to assess risk for.
function hasResolvedLocation(selection: VillageSelection): boolean {
  if (selection.kind === "village") return true;
  if (selection.kind === "other") return selection.customName.trim().length > 0;
  return false;
}

export default function AgentPage() {
  const [villageSelection, setVillageSelection] = useState<VillageSelection>({
    kind: "none",
  });
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
    getLocationFields: () => locationFields(villageSelection),
  });

  async function handleSend() {
    const trimmed = inputText.trim();
    if (!trimmed || isPending || !hasResolvedLocation(villageSelection)) return;
    setInputText("");
    await sendMessage(trimmed);
  }

  const hasLocation = hasResolvedLocation(villageSelection);

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
            <Compass className="size-6 text-primary" aria-hidden="true" />
            Flood-Aware Agent
          </h1>
          <p className="text-sm text-muted-foreground">
            Grounded, evidence-based flood risk answers for Swat district.
          </p>
        </div>
        <NewConversationButton
          onClick={resetConversation}
          disabled={messages.length === 0}
        />
      </header>

      <div className="shrink-0">
        <VillageSelector
          selection={villageSelection}
          onSelectionChange={setVillageSelection}
          disabled={isPending}
        />
      </div>

      <div
        role="log"
        aria-live="polite"
        className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto py-2"
      >
        {messages.length === 0 && (
          <p className="m-auto max-w-sm text-center text-sm text-muted-foreground">
            Select a village above, then ask a question about flood risk,
            evacuation, or shelter capacity.
          </p>
        )}

        {messages.map((message) => (
          <ChatMessageBubble key={message.id} message={message} />
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
          placeholder={
            hasLocation
              ? "Ask about flood risk, evacuation routes, shelter capacity..."
              : "Select a village above to begin"
          }
          disabled={isPending || !hasLocation}
          rows={1}
          className="min-h-10 max-h-40 resize-none"
        />
        <Button
          type="submit"
          size="icon"
          disabled={isPending || !hasLocation || !inputText.trim()}
          aria-label="Send message"
        >
          <Send className="size-4" aria-hidden="true" />
        </Button>
      </form>
    </PageShell>
  );
}
