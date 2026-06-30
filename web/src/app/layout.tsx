import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Sidebar } from "@/components/Sidebar";
import "./globals.css";

export const metadata: Metadata = {
  title: "ProcureMind AI",
  description: "Schema-driven procurement intelligence workspace"
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <Sidebar />
        <main className="min-h-screen pl-[260px]">
          <div className="min-h-screen bg-slate-50">{children}</div>
        </main>
      </body>
    </html>
  );
}
