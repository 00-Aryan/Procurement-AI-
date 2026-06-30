import { ArrowRight, Clock3 } from "lucide-react";

type ComingSoonFallbackProps = {
  featureName: string;
  businessObjective: string;
};

export function ComingSoonFallback({ featureName, businessObjective }: ComingSoonFallbackProps) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6 py-12">
      <section className="w-full max-w-3xl rounded-lg border border-slate-200 bg-white p-8 text-center shadow-soft">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
          <Clock3 className="h-7 w-7" />
        </div>

        <p className="mt-6 text-xs font-bold uppercase tracking-normal text-indigo-600">
          Version 2.0 Core Scalability Roadmap
        </p>
        <h1 className="mt-3 text-3xl font-bold tracking-normal text-slate-950">{featureName}</h1>
        <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-slate-600">
          {featureName} is currently scheduled for deployment under the Version 2.0 Core Scalability Roadmap.
          This module will automate {businessObjective}.
        </p>

        <button
          type="button"
          className="mx-auto mt-8 inline-flex h-12 items-center justify-center gap-2 rounded-md bg-indigo-600 px-6 text-sm font-semibold text-white shadow-panel transition hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
        >
          Join Operational Beta Testing Priority Queue
          <ArrowRight className="h-4 w-4" />
        </button>
      </section>
    </div>
  );
}
