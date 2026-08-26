import { AlertTriangle, Info } from "lucide-react";
import type { VariantProps } from "class-variance-authority";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge, badgeVariants } from "@/components/ui/badge";
import type {
  ActionResponse,
  DecisionConfidence,
  Priority,
  RiskLevel,
} from "@/types";

type BadgeVariant = VariantProps<typeof badgeVariants>["variant"];

/** Badge has no dedicated "low" risk tier -- the lowest factual risk level renders with the same (safe/green) treatment as "normal". */
const RISK_BADGE_VARIANT: Record<RiskLevel, BadgeVariant> = {
  normal: "risk-normal",
  low: "risk-normal",
  moderate: "risk-moderate",
  high: "risk-high",
  extreme: "risk-extreme",
};

const RISK_LABEL: Record<RiskLevel, string> = {
  normal: "Normal",
  low: "Low",
  moderate: "Moderate",
  high: "High",
  extreme: "Extreme",
};

/** Confidence is a distinct axis from risk -- reuse the neutral badge variants rather than borrowing risk-severity colors. */
const CONFIDENCE_BADGE_VARIANT: Record<DecisionConfidence, BadgeVariant> = {
  high: "default",
  medium: "secondary",
  low: "outline",
};

const PRIORITY_STYLE: Record<Priority, { label: string; className: string }> = {
  critical: { label: "Critical", className: "text-risk-extreme" },
  high: { label: "High", className: "text-risk-high" },
  medium: { label: "Medium", className: "text-risk-moderate" },
  low: { label: "Low", className: "text-muted-foreground" },
};

/** Plain-language phrases for the fixed evidence-category vocabulary the backend emits (see backend/app/decision/prompt_builder.py). */
const MISSING_EVIDENCE_PHRASES: Record<string, string> = {
  forecast: "an updated flood forecast",
  gis: "local flood-zone mapping",
  weather: "current weather data",
  knowledge: "government guidance documents",
  shelter: "shelter information",
  village: "village-level details",
};

/** Matches the stale-forecast notice, e.g. "forecast (data is approximately 3 days old)". */
const STALE_FORECAST_PATTERN = /^forecast \(data is approximately (\d+) days? old\)$/i;

const missingEvidenceListFormatter = new Intl.ListFormat("en", {
  style: "long",
  type: "disjunction",
});

function describeMissingEvidenceCategory(category: string): string {
  const staleMatch = category.match(STALE_FORECAST_PATTERN);
  if (staleMatch) {
    const days = staleMatch[1];
    return `a fresher flood forecast (the one on file is about ${days} day${
      days === "1" ? "" : "s"
    } old)`;
  }
  return MISSING_EVIDENCE_PHRASES[category] ?? category;
}

function formatMissingEvidenceSentence(categories: string[]): string {
  const phrases = categories.map(describeMissingEvidenceCategory);
  return `This assessment doesn't yet include ${missingEvidenceListFormatter.format(phrases)}.`;
}

export interface AssistantDecision {
  risk_level: RiskLevel | null;
  confidence: DecisionConfidence | null;
  summary: string;
  actions: ActionResponse[];
  citations: string[];
  missing_evidence: string[];
}

export interface ChatMessageData {
  id: string;
  role: "user" | "assistant" | "error";
  content: string;
  decision?: AssistantDecision;
}

interface ChatMessageBubbleProps {
  message: ChatMessageData;
  /** Risk/confidence badges only make sense for flood-risk assessments -- pages asking non-risk questions (e.g. policy guidance) should hide them. */
  showRiskBadges?: boolean;
}

export function ChatMessageBubble({
  message,
  showRiskBadges = true,
}: ChatMessageBubbleProps) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <p className="max-w-[85%] animate-in fade-in slide-in-from-bottom-2 rounded-2xl rounded-br-sm border border-primary/30 bg-primary/10 px-4 py-2.5 text-sm text-foreground duration-[250ms]">
          {message.content}
        </p>
      </div>
    );
  }

  if (message.role === "error") {
    return (
      <div className="flex justify-start">
        <div className="flex max-w-[85%] animate-in fade-in slide-in-from-bottom-2 items-start gap-2 rounded-2xl rounded-bl-sm border border-destructive/40 bg-destructive/10 px-4 py-2.5 text-sm text-destructive duration-[250ms]">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <p>{message.content}</p>
        </div>
      </div>
    );
  }

  const decision = message.decision;

  return (
    <div className="flex justify-start">
      <div className="flex max-w-[85%] animate-in fade-in slide-in-from-bottom-2 flex-col gap-3 rounded-2xl rounded-bl-sm border border-border bg-card px-4 py-3 text-sm text-card-foreground duration-[250ms]">
        {decision && showRiskBadges && decision.risk_level && decision.confidence && (
          <div className="flex animate-in fade-in fill-mode-backwards flex-wrap items-center gap-2 duration-[200ms]">
            <Badge variant={RISK_BADGE_VARIANT[decision.risk_level]}>
              {RISK_LABEL[decision.risk_level]} risk
            </Badge>
            <Badge variant={CONFIDENCE_BADGE_VARIANT[decision.confidence]}>
              {decision.confidence} confidence
            </Badge>
          </div>
        )}

        <p className="animate-in fade-in fill-mode-backwards text-foreground duration-[200ms] delay-[70ms]">
          {message.content}
        </p>

        {decision && decision.actions.length > 0 && (
          <ul className="flex animate-in fade-in fill-mode-backwards flex-col gap-1.5 duration-[200ms] delay-[140ms]">
            {decision.actions.map((action, index) => (
              <li key={index} className="flex gap-2 text-sm">
                <span
                  className={`shrink-0 font-semibold ${PRIORITY_STYLE[action.priority].className}`}
                >
                  {PRIORITY_STYLE[action.priority].label}
                </span>
                <span className="text-foreground">{action.action}</span>
              </li>
            ))}
          </ul>
        )}

        {decision && decision.missing_evidence.length > 0 && (
          <p className="flex items-start gap-1.5 text-xs text-muted-foreground/80">
            <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
            <span>{formatMissingEvidenceSentence(decision.missing_evidence)}</span>
          </p>
        )}

        {decision && decision.citations.length > 0 && (
          <Accordion
            type="single"
            collapsible
            className="animate-in fade-in fill-mode-backwards duration-[200ms] delay-[210ms]"
          >
            <AccordionItem value="citations" className="border-none">
              <AccordionTrigger className="py-1 text-xs text-muted-foreground hover:no-underline">
                {decision.citations.length} citation
                {decision.citations.length === 1 ? "" : "s"}
              </AccordionTrigger>
              <AccordionContent className="pb-0">
                <ul className="flex flex-col gap-1 text-xs text-muted-foreground">
                  {decision.citations.map((citation, index) => (
                    <li key={index}>{citation}</li>
                  ))}
                </ul>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        )}
      </div>
    </div>
  );
}
