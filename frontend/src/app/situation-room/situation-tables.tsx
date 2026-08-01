"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronUp, ChevronsUpDown } from "lucide-react";

import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ShelterResponse, VillageResponse } from "@/types";

type SortDirection = "asc" | "desc";

interface SortState<T> {
  key: keyof T;
  direction: SortDirection;
}

function sortRows<T>(rows: T[], key: keyof T, direction: SortDirection): T[] {
  return [...rows].sort((a, b) => {
    const av = a[key];
    const bv = b[key];
    if (av == null) return 1;
    if (bv == null) return -1;
    if (typeof av === "number" && typeof bv === "number") {
      return direction === "asc" ? av - bv : bv - av;
    }
    const comparison = String(av).localeCompare(String(bv));
    return direction === "asc" ? comparison : -comparison;
  });
}

interface Column<T> {
  key: keyof T;
  label: string;
  align?: "right";
  format?: (row: T) => string;
}

interface DataTableProps<T extends { name: string }> {
  title: string;
  rows: T[];
  columns: Column<T>[];
  sort: SortState<T>;
  onSort: (key: keyof T) => void;
}

function DataTable<T extends { name: string }>({
  title,
  rows,
  columns,
  sort,
  onSort,
}: DataTableProps<T>) {
  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      <div className="overflow-x-auto rounded-xl border border-border">
        <table className="w-full min-w-[420px] text-left text-sm">
          <thead className="border-b border-border bg-muted/40 text-xs text-muted-foreground">
            <tr>
              {columns.map((column) => (
                <th
                  key={String(column.key)}
                  scope="col"
                  className={`px-3 py-2 font-medium ${column.align === "right" ? "text-right" : "text-left"}`}
                >
                  <button
                    type="button"
                    onClick={() => onSort(column.key)}
                    className="inline-flex items-center gap-1 hover:text-foreground"
                  >
                    {column.label}
                    {sort.key === column.key ? (
                      sort.direction === "asc" ? (
                        <ChevronUp className="size-3" aria-hidden="true" />
                      ) : (
                        <ChevronDown className="size-3" aria-hidden="true" />
                      )
                    ) : (
                      <ChevronsUpDown
                        className="size-3 opacity-40"
                        aria-hidden="true"
                      />
                    )}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-3 py-6 text-center text-muted-foreground"
                >
                  No records for this district.
                </td>
              </tr>
            ) : (
              rows.map((row, index) => (
                <tr key={`${row.name}-${index}`} className="hover:bg-muted/30">
                  {columns.map((column) => (
                    <td
                      key={String(column.key)}
                      className={`px-3 py-2 text-foreground ${column.align === "right" ? "text-right tabular-nums" : "text-left"}`}
                    >
                      {column.format
                        ? column.format(row)
                        : String(row[column.key])}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const ALL_DISTRICTS = "__all__";

interface SituationTablesProps {
  villages: VillageResponse[];
  shelters: ShelterResponse[];
}

export function SituationTables({ villages, shelters }: SituationTablesProps) {
  const districts = useMemo(() => {
    const set = new Set<string>();
    villages.forEach((v) => set.add(v.district));
    shelters.forEach((s) => set.add(s.district));
    return [...set].sort();
  }, [villages, shelters]);

  const [district, setDistrict] = useState(ALL_DISTRICTS);
  const [villageSort, setVillageSort] = useState<SortState<VillageResponse>>({
    key: "name",
    direction: "asc",
  });
  const [shelterSort, setShelterSort] = useState<SortState<ShelterResponse>>({
    key: "name",
    direction: "asc",
  });

  const filteredVillages = useMemo(() => {
    const rows =
      district === ALL_DISTRICTS
        ? villages
        : villages.filter((v) => v.district === district);
    return sortRows(rows, villageSort.key, villageSort.direction);
  }, [villages, district, villageSort]);

  const filteredShelters = useMemo(() => {
    const rows =
      district === ALL_DISTRICTS
        ? shelters
        : shelters.filter((s) => s.district === district);
    return sortRows(rows, shelterSort.key, shelterSort.direction);
  }, [shelters, district, shelterSort]);

  function toggleVillageSort(key: keyof VillageResponse) {
    setVillageSort((prev) =>
      prev.key === key
        ? { key, direction: prev.direction === "asc" ? "desc" : "asc" }
        : { key, direction: "asc" }
    );
  }

  function toggleShelterSort(key: keyof ShelterResponse) {
    setShelterSort((prev) =>
      prev.key === key
        ? { key, direction: prev.direction === "asc" ? "desc" : "asc" }
        : { key, direction: "asc" }
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <Label htmlFor="district-filter" className="text-sm text-muted-foreground">
          Filter by district
        </Label>
        <Select value={district} onValueChange={setDistrict}>
          <SelectTrigger id="district-filter" size="sm" className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_DISTRICTS}>All districts</SelectItem>
            {districts.map((d) => (
              <SelectItem key={d} value={d}>
                {d}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <DataTable
          title={`Villages (${filteredVillages.length})`}
          rows={filteredVillages}
          sort={villageSort}
          onSort={toggleVillageSort}
          columns={[
            { key: "name", label: "Name" },
            { key: "district", label: "District" },
            {
              key: "population",
              label: "Population",
              align: "right",
              format: (row) =>
                row.population === null
                  ? "—"
                  : row.population.toLocaleString(),
            },
          ]}
        />
        <DataTable
          title={`Shelters (${filteredShelters.length})`}
          rows={filteredShelters}
          sort={shelterSort}
          onSort={toggleShelterSort}
          columns={[
            { key: "name", label: "Name" },
            { key: "district", label: "District" },
            {
              key: "capacity",
              label: "Capacity",
              align: "right",
              format: (row) => row.capacity.toLocaleString(),
            },
          ]}
        />
      </div>
    </div>
  );
}
