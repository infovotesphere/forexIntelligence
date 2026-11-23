import type { Metadata } from "next";
import { AuthGate } from "@/components/AuthGate";
import "./globals.css";

export const metadata: Metadata = {
  title: "Forex Intelligence",
  description: "Institutional forex trading intelligence platform",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return <html lang="en"><body><AuthGate>{children}</AuthGate></body></html>;
}
