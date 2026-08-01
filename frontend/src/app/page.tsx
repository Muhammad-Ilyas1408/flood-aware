import Link from "next/link";
import { Compass, ClipboardList, Map } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageShell } from "@/components/ui/page-shell";
import { getDatasetCatalog } from "@/lib/api-client";

interface HeroStat {
  label: string;
  value: number;
}

/** Soft-fails on an unreachable backend -- a landing page should never crash or show an error banner over a missing stat. */
async function getHeroStats(): Promise<HeroStat[] | null> {
  try {
    const catalog = await getDatasetCatalog({ cache: "no-store" });
    return [
      {
        label: "Villages monitored",
        value: catalog.villages.statistics.record_count,
      },
      {
        label: "Shelters tracked",
        value: catalog.shelters.statistics.record_count,
      },
    ];
  } catch {
    return null;
  }
}

const FEATURES = [
  {
    href: "/agent",
    icon: Compass,
    title: "Flood-Aware Agent",
    description:
      "Ask questions in plain language and get grounded, evidence-cited flood risk answers for any village or shelter in Swat.",
  },
  {
    href: "/policy-advisor",
    icon: ClipboardList,
    title: "Policy Advisor",
    description:
      "Ask about government flood policy, disaster-management plans, and official guidance — grounded in real PDMA and NDMP documents.",
  },
  {
    href: "/situation-room",
    icon: Map,
    title: "Situation Room",
    description:
      "See villages, shelters, and current risk levels together on a live map of the district.",
  },
] as const;

export default async function Home() {
  const stats = await getHeroStats();

  return (
    <PageShell>
      <section className="flex flex-col items-center gap-6 py-8 text-center sm:py-14">
        <div className="flex max-w-3xl flex-col items-center gap-4">
          <h1 className="animate-in fade-in slide-in-from-bottom-4 font-heading text-4xl font-semibold tracking-tight text-foreground duration-700 sm:text-5xl lg:text-6xl">
            Flood-Aware
          </h1>
          <p className="max-w-2xl animate-in fade-in slide-in-from-bottom-4 fill-mode-backwards text-lg text-muted-foreground duration-700 delay-150 sm:text-xl">
            Grounded, evidence-based flood decision support for Swat
            district — every answer traced back to real village, shelter,
            and hydrological data.
          </p>
        </div>

        {stats && (
          <dl className="flex animate-in fade-in slide-in-from-bottom-4 fill-mode-backwards flex-wrap justify-center gap-x-10 gap-y-4 pt-2 duration-700 delay-300">
            {stats.map((stat) => (
              <div key={stat.label} className="flex flex-col gap-1">
                <dt className="text-sm text-muted-foreground">
                  {stat.label}
                </dt>
                <dd className="font-heading text-3xl font-semibold text-foreground sm:text-4xl">
                  {stat.value.toLocaleString()}
                </dd>
              </div>
            ))}
          </dl>
        )}
      </section>

      <section className="flex flex-col gap-6 pb-12 sm:pb-16">
        <h2 className="text-xl font-semibold text-foreground sm:text-2xl">
          Explore Flood-Aware
        </h2>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ href, icon: Icon, title, description }) => (
            <Link
              key={href}
              href={href}
              className="group rounded-xl outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              <Card className="h-full transition-all duration-200 group-hover:-translate-y-1 group-hover:border-primary/50 group-hover:shadow-xl group-hover:shadow-primary/10 group-focus-visible:-translate-y-1 group-focus-visible:border-primary/50 group-focus-visible:shadow-xl group-focus-visible:shadow-primary/10">
                <CardHeader className="gap-3">
                  <Icon
                    className="size-6 text-primary transition-transform duration-200 group-hover:scale-110 group-focus-visible:scale-110"
                    aria-hidden="true"
                  />
                  <CardTitle className="text-lg">{title}</CardTitle>
                  <CardDescription>{description}</CardDescription>
                </CardHeader>
                <CardContent className="text-sm font-medium text-primary opacity-0 transition-opacity duration-200 group-hover:opacity-100 group-focus-visible:opacity-100">
                  Open &rarr;
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </section>
    </PageShell>
  );
}
