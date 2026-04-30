import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Atomadic — Investor Overview",
  description:
    "One developer. Two months. No funding. Building the architectural control plane for AI-generated code — and the inference layer that guarantees it.",
  openGraph: {
    title: "Atomadic — Investor Overview",
    description:
      "Three connected products: the architecture compiler AI agents wrap around, the inference API that returns Lean4-attested responses, and the sovereign AI built on both.",
    type: "website",
    url: "https://investor.atomadic.tech",
  },
  twitter: {
    card: "summary_large_image",
    title: "Atomadic — Investor Overview",
    description: "841 tests. 0 violations. $7.65B market. One developer.",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="scanlines">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,100..800;1,100..800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-cyber-dark text-cyber-chrome antialiased">{children}</body>
    </html>
  );
}
