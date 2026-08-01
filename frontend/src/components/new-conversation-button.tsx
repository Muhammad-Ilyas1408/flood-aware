import { RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";

interface NewConversationButtonProps {
  onClick: () => void;
  disabled?: boolean;
}

/** Shared by Agent and Policy Advisor -- a clear secondary action, deliberately not competing with the primary send button. */
export function NewConversationButton({
  onClick,
  disabled,
}: NewConversationButtonProps) {
  return (
    <Button
      variant="outline"
      onClick={onClick}
      disabled={disabled}
      className="gap-2 border-border px-3.5 text-foreground transition-colors hover:border-primary/50 hover:bg-primary/5 hover:text-primary"
    >
      <RotateCcw className="size-4" aria-hidden="true" />
      Start new conversation
    </Button>
  );
}
