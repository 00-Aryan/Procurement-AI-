import Link from "next/link";
import { Bell, Menu, Search } from "lucide-react";

import { ComingSoonTooltip } from "@/components/Tooltip";
import { dashboardMetrics, gettingStartedSteps, insightCards } from "@/lib/dashboard";

export default function HomePage() {
  return (
    <div className="relative min-h-screen overflow-hidden px-12 py-8">
      <div className="pointer-events-none absolute inset-x-0 top-16 h-56 bg-[radial-gradient(circle_at_50%_20%,rgba(99,102,241,0.10),transparent_36%)]" />
      <div className="pointer-events-none absolute left-0 right-0 top-40 h-px bg-indigo-100" />

      <header className="relative z-10 flex items-center justify-between">
        <button className="flex h-12 w-12 items-center justify-center rounded-full border border-slate-200 bg-white text-indigo-600 shadow-soft" aria-label="Open navigation">
          <Menu className="h-6 w-6" />
        </button>
        <div className="flex items-center gap-5">
          <button className="relative text-slate-600" aria-label="Notifications">
            <Bell className="h-5 w-5" />
            <span className="absolute -right-1 -top-1 h-4 min-w-4 rounded-full bg-rose-500 px-1 text-[10px] font-bold leading-4 text-white">
              3
            </span>
          </button>
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-600 text-sm font-semibold text-white">
            AS
          </div>
        </div>
      </header>

      <section className="relative z-10 mx-auto mt-12 max-w-5xl text-center">
        <h1 className="text-4xl font-bold tracking-normal text-slate-950">Welcome back, Aryan</h1>
        <p className="mt-4 text-lg text-slate-600">What would you like to explore today?</p>
        <ComingSoonTooltip className="mt-10 w-full max-w-xl" text="Feature coming soon in V2">
          <div className="flex h-14 w-full items-center gap-3 rounded-full border border-slate-200 bg-white px-6 text-left text-sm text-slate-400 shadow-soft">
            <Search className="h-5 w-5 text-slate-400" />
            <span className="truncate">Search for insights, reports, products, suppliers...</span>
          </div>
        </ComingSoonTooltip>
      </section>

      <section className="relative z-10 mx-auto mt-16 max-w-7xl">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-slate-950">Explore Insights</h2>
          <p className="mt-2 text-sm text-slate-500">Choose an area to get started</p>
        </div>

        <div className="mt-8 grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-6">
          {insightCards.map((card) => {
            const Icon = card.icon;
            const content = (
              <Link
                href={card.href}
                className="group flex h-64 flex-col items-center rounded-lg border border-slate-200 bg-white p-6 text-center shadow-soft transition hover:-translate-y-1 hover:border-indigo-200 hover:shadow-panel"
              >
                <div className="flex h-20 w-20 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
                  <Icon className="h-10 w-10" />
                </div>
                <h3 className="mt-6 text-base font-bold text-slate-950">{card.title}</h3>
                <p className="mt-3 min-h-16 text-sm leading-6 text-slate-600">{card.description}</p>
                <span className="mt-auto flex h-10 w-10 items-center justify-center rounded-full bg-indigo-50 text-indigo-600 transition group-hover:bg-indigo-600 group-hover:text-white">
                  <span className="text-2xl leading-none">→</span>
                </span>
              </Link>
            );

            return card.comingSoon ? (
              <ComingSoonTooltip key={card.title} className="w-full" text="Feature coming soon in V2">
                {content}
              </ComingSoonTooltip>
            ) : (
              <div key={card.title}>{content}</div>
            );
          })}
        </div>
      </section>

      <section className="relative z-10 mx-auto mt-8 grid max-w-7xl grid-cols-1 gap-4 rounded-lg border border-indigo-100 bg-white/80 p-6 shadow-soft backdrop-blur md:grid-cols-4">
        {gettingStartedSteps.map((step, index) => {
          const Icon = step.icon;
          return (
            <div key={step.title} className="flex items-center gap-4">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
                <Icon className="h-7 w-7" />
              </div>
              <div className="min-w-0">
                <h3 className="text-sm font-bold text-slate-950">{step.title}</h3>
                <p className="mt-1 text-sm leading-5 text-slate-600">{step.detail}</p>
              </div>
              {index < gettingStartedSteps.length - 1 ? <span className="ml-auto hidden text-slate-300 md:block">›</span> : null}
            </div>
          );
        })}
      </section>

      <section className="relative z-10 mx-auto mt-8 grid max-w-7xl grid-cols-1 gap-4 md:grid-cols-4">
        {dashboardMetrics.map((metric) => (
          <div key={metric.label} className="rounded-lg border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-xs font-semibold uppercase text-slate-400">{metric.label}</div>
            <div className="mt-3 truncate text-lg font-bold text-slate-950">{metric.value}</div>
            <div className="mt-1 text-sm text-indigo-600">{metric.detail}</div>
          </div>
        ))}
      </section>
    </div>
  );
}
