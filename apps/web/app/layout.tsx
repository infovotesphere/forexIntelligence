import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Forex Intelligence",
  description: "Institutional forex trading intelligence platform",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return <html lang="en"><body>{children}</body></html>;
}
