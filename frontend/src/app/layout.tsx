import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";

import { AppHeader } from "@/components/AppHeader";
import { Providers } from "@/components/Providers";

import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });
const jetbrains = JetBrains_Mono({ variable: "--font-jetbrains", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AuditGlimmer — Physical asset reconciliation",
  description:
    "Reconcile a physical-asset ledger against warehouse photos with segmentation, structured evidence and human review.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrains.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-2 focus:z-50 focus:rounded focus:bg-surface-3 focus:px-3 focus:py-2"
        >
          Skip to content
        </a>
        <Providers>
          <AppHeader />
          <main id="main" className="mx-auto w-full max-w-[1440px] flex-1 px-4 py-6 sm:px-6">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  );
}
