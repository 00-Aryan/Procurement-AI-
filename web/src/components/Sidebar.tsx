"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bot, ChevronDown, Sparkles } from "lucide-react";

import { navItems, tenantProfile } from "@/lib/dashboard";
import { ComingSoonTooltip } from "@/components/Tooltip";

function NavLink({ item }: { item: (typeof navItems)[number] }) {
  const pathname = usePathname();
  const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
  const Icon = item.icon;
  const link = (
    <Link
      href={item.href}
      className={`flex h-11 w-full items-center gap-3 rounded-md px-4 text-sm font-medium transition ${
        isActive
          ? "bg-indigo-50 text-indigo-600"
          : "text-slate-600 hover:bg-slate-50 hover:text-indigo-600"
      }`}
    >
      <Icon className="h-4 w-4 shrink-0" />
      <span className="truncate">{item.label}</span>
    </Link>
  );

  if (item.comingSoon) {
    return (
      <ComingSoonTooltip className="w-full" text="Feature coming soon in V2">
        {link}
      </ComingSoonTooltip>
    );
  }

  return link;
}

export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-30 flex w-[260px] flex-col border-r border-slate-200 bg-white px-5 py-6">
      <Link href="/" className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-100 text-indigo-600">
          <Sparkles className="h-6 w-6" />
        </div>
        <div>
          <div className="text-lg font-bold text-slate-950">ProcureMind AI</div>
          <div className="text-[11px] font-medium text-slate-500">Intelligence for Smarter Procurement</div>
        </div>
      </Link>

      <nav className="mt-9 flex flex-1 flex-col gap-2">
        {navItems.map((item) => (
          <NavLink key={item.label} item={item} />
        ))}
      </nav>

      <div className="space-y-5">
        <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-soft">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-600 text-sm font-semibold text-white">
            AS
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-semibold text-slate-900">Aryan Sharma</div>
            <div className="text-xs text-slate-500">Admin</div>
          </div>
          <ChevronDown className="h-4 w-4 text-slate-400" />
        </div>

        <div className="relative overflow-hidden rounded-lg bg-indigo-600 p-4 text-white shadow-panel">
          <div className="absolute -right-7 -top-8 h-24 w-24 rounded-full bg-white/15" />
          <div className="relative flex items-center gap-2 text-xs font-semibold text-indigo-100">
            <Bot className="h-4 w-4" />
            Ask ProcureMind AI
          </div>
          <p className="relative mt-3 text-sm leading-6 text-indigo-50">
            Your AI copilot for procurement insights and recommendations.
          </p>
          <Link
            href="/copilot"
            className="relative mt-5 inline-flex h-9 items-center rounded-md bg-white px-4 text-xs font-semibold text-indigo-600"
          >
            Chat with AI
          </Link>
        </div>
      </div>
    </aside>
  );
}
