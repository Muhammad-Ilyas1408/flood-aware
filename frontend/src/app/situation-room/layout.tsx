import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Situation Room — Flood-Aware",
  description:
    "A live district overview of every village and shelter Flood-Aware tracks, mapped from real coordinates.",
};

export default function SituationRoomLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return children;
}
