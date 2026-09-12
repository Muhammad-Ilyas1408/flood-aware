import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Flood Guide — Flood-Aware",
  description:
    "Ask grounded, evidence-based flood risk questions for any village or shelter in Swat.",
};

export default function AgentLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return children;
}
