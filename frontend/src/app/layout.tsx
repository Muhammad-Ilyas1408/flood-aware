import type { Metadata } from "next";
import "./globals.css";
import { Inter, Space_Grotesk } from "next/font/google";
import { cn } from "@/lib/utils";
import { SiteHeader } from "@/components/site-header";

const bodyFont = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const headingFont = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-heading",
});

export const metadata: Metadata = {
  title: "Flood-Aware",
  description:
    "Flood-Aware: grounded flood risk decision support for Swat, Khyber Pakhtunkhwa.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={cn("font-sans", bodyFont.variable, headingFont.variable)}
    >
      <body>
        <SiteHeader />
        {children}
      </body>
    </html>
  );
}
