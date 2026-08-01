"use client";

import { useEffect, useState } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getVillages } from "@/lib/api-client";
import type { VillageResponse } from "@/types";

export type VillageSelection =
  | { kind: "none" }
  | { kind: "village"; village: VillageResponse }
  | { kind: "other"; customName: string };

const OTHER_VALUE = "__other__";

interface VillageSelectorProps {
  selection: VillageSelection;
  onSelectionChange: (selection: VillageSelection) => void;
  disabled?: boolean;
}

export function VillageSelector({
  selection,
  onSelectionChange,
  disabled,
}: VillageSelectorProps) {
  const [villages, setVillages] = useState<VillageResponse[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">(
    "loading"
  );

  useEffect(() => {
    let cancelled = false;

    getVillages()
      .then((response) => {
        if (cancelled) return;
        setVillages(response.data);
        setLoadState("ready");
      })
      .catch(() => {
        if (cancelled) return;
        setLoadState("error");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const selectValue =
    selection.kind === "village"
      ? String(villages.indexOf(selection.village))
      : selection.kind === "other"
        ? OTHER_VALUE
        : undefined;

  function handleValueChange(value: string) {
    if (value === OTHER_VALUE) {
      onSelectionChange({ kind: "other", customName: "" });
      return;
    }
    const village = villages[Number(value)];
    if (village) {
      onSelectionChange({ kind: "village", village });
    }
  }

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:gap-3">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="village-select">Village</Label>
        <Select
          value={selectValue}
          onValueChange={handleValueChange}
          disabled={disabled || loadState === "loading"}
        >
          <SelectTrigger id="village-select" className="w-full sm:w-64">
            <SelectValue
              placeholder={
                loadState === "loading"
                  ? "Loading villages..."
                  : loadState === "error"
                    ? "Couldn't load villages"
                    : "Select a village..."
              }
            />
          </SelectTrigger>
          <SelectContent>
            {villages.map((village, index) => (
              <SelectItem key={`${village.name}-${index}`} value={String(index)}>
                {village.name} ({village.district})
              </SelectItem>
            ))}
            <SelectItem value={OTHER_VALUE}>Other / not listed</SelectItem>
          </SelectContent>
        </Select>
        {loadState === "error" && (
          <p className="text-xs text-destructive">
            Couldn&apos;t load the village list. You can still continue with
            &ldquo;Other / not listed&rdquo;.
          </p>
        )}
      </div>

      {selection.kind === "other" && (
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="village-custom-name">Village name (optional)</Label>
          <Input
            id="village-custom-name"
            placeholder="e.g. a hamlet not in our records"
            value={selection.customName}
            disabled={disabled}
            onChange={(event) =>
              onSelectionChange({
                kind: "other",
                customName: event.target.value,
              })
            }
            className="sm:w-64"
          />
        </div>
      )}
    </div>
  );
}
