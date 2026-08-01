import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Policy Advisor — Flood-Aware",
  description:
    "Ask about government flood policy, disaster-management plans, and official guidance.",
};

export default function PolicyAdvisorLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return children;
}
