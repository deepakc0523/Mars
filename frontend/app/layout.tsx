import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "MARS — Multi-Agent Reasoning & Adaptive Response System",
    template: "%s | MARS",
  },
  description:
    "Real-time incident-response agent with interruptible execution, " +
    "multi-agent verification, and an adaptive planning loop.",
  keywords: ["incident response", "AI agents", "MARS", "real-time", "adaptive"],
  authors: [{ name: "MARS Team" }],
  robots: "noindex,nofollow", // Not public during hackathon
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
        {children}
      </body>
    </html>
  );
}
