"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Menu } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PageShell } from "@/components/ui/page-shell";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Home" },
  { href: "/agent", label: "Flood-Aware Agent" },
  { href: "/policy-advisor", label: "Policy Advisor" },
  { href: "/situation-room", label: "Situation Room" },
] as const;

interface NavLinkProps {
  href: string;
  label: string;
  isActive: boolean;
  onNavigate?: () => void;
  /** "underline" for the horizontal desktop bar, "block" for the stacked mobile sheet. */
  variant?: "underline" | "block";
}

function NavLink({
  href,
  label,
  isActive,
  onNavigate,
  variant = "underline",
}: NavLinkProps) {
  if (variant === "block") {
    return (
      <Link
        href={href}
        aria-current={isActive ? "page" : undefined}
        onClick={onNavigate}
        className={cn(
          "rounded-lg px-3 py-2 text-sm font-medium outline-none transition-colors duration-200 focus-visible:ring-3 focus-visible:ring-ring/50",
          isActive
            ? "bg-primary/10 text-primary"
            : "text-muted-foreground hover:bg-muted hover:text-foreground"
        )}
      >
        {label}
      </Link>
    );
  }

  return (
    <Link
      href={href}
      aria-current={isActive ? "page" : undefined}
      onClick={onNavigate}
      className={cn(
        "group relative w-fit rounded-md px-1 py-1.5 text-sm font-medium outline-none transition-colors duration-200 focus-visible:ring-3 focus-visible:ring-ring/50",
        isActive
          ? "text-foreground"
          : "text-muted-foreground hover:text-foreground"
      )}
    >
      {label}
      <span
        aria-hidden="true"
        className={cn(
          "absolute inset-x-1 -bottom-0.5 h-0.5 origin-left rounded-full bg-primary transition-transform duration-300 ease-out",
          isActive
            ? "scale-x-100"
            : "scale-x-0 group-hover:scale-x-100 group-hover:bg-primary/40"
        )}
      />
    </Link>
  );
}

export function SiteHeader() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur-sm duration-500 animate-in fade-in slide-in-from-top-2 supports-backdrop-filter:bg-background/60">
      <PageShell className="flex h-14 items-center justify-between py-0 sm:h-16 sm:py-0">
        <Link
          href="/"
          className="rounded-md px-1 font-heading text-lg font-semibold tracking-tight text-foreground outline-none transition-colors hover:text-primary focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          Flood-Aware
        </Link>

        <nav className="hidden items-center gap-6 sm:flex" aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.href}
              href={item.href}
              label={item.label}
              isActive={pathname === item.href}
            />
          ))}
        </nav>

        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
          <SheetTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="sm:hidden"
              aria-label="Open navigation menu"
            >
              <Menu className="size-5" aria-hidden="true" />
            </Button>
          </SheetTrigger>
          <SheetContent side="right" className="w-64">
            <SheetHeader>
              <SheetTitle>Flood-Aware</SheetTitle>
            </SheetHeader>
            <nav className="flex flex-col gap-1 px-4" aria-label="Primary">
              {NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.href}
                  href={item.href}
                  label={item.label}
                  isActive={pathname === item.href}
                  onNavigate={() => setMobileOpen(false)}
                  variant="block"
                />
              ))}
            </nav>
          </SheetContent>
        </Sheet>
      </PageShell>
    </header>
  );
}
