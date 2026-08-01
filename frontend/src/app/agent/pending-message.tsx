"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

interface PendingMessageBubbleProps {
  statusMessage: string;
}

/**
 * Cross-fades between rotating status strings via a CSS opacity transition
 * driven by `onTransitionEnd`, not a timer -- the rotation cadence itself
 * lives in useConversation's interval and is untouched here.
 */
export function PendingMessageBubble({
  statusMessage,
}: PendingMessageBubbleProps) {
  const [displayedMessage, setDisplayedMessage] = useState(statusMessage);
  const [fadingOut, setFadingOut] = useState(false);

  if (statusMessage !== displayedMessage && !fadingOut) {
    setFadingOut(true);
  }

  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm border border-border bg-card px-4 py-2.5 text-sm text-muted-foreground">
        <Loader2 className="size-4 shrink-0 animate-spin" aria-hidden="true" />
        <span
          className={cn(
            "inline-block transition-opacity duration-150 ease-out",
            fadingOut ? "opacity-0" : "opacity-100"
          )}
          onTransitionEnd={() => {
            if (fadingOut) {
              setDisplayedMessage(statusMessage);
              setFadingOut(false);
            }
          }}
        >
          {displayedMessage}
        </span>
      </div>
    </div>
  );
}
