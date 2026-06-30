import { Lightbulb, Sparkles } from "lucide-react";

const recommendations = [
  ["Reorder Coffee Beans", "Current stock will last only 5 days. Reorder 100 kg to avoid stockout.", "High", "₹ 1.2 Cr"],
  ["Switch Supplier for Sugar Syrup", "New supplier offers 8% lower price with similar quality.", "Medium", "₹ 48 Lakhs"],
  ["Reduce Excess Inventory", "18 items are overstocked. Consider reducing order quantities.", "Medium", "₹ 35 Lakhs"]
];

export default function RecommendationsPage() {
  return (
    <div className="min-h-screen px-12 py-10">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-950">Recommendations</h1>
          <p className="mt-2 text-sm text-slate-600">AI-powered recommendations to optimize procurement decisions.</p>
        </div>
        <div className="flex h-10 items-center gap-2 rounded-md border border-indigo-100 bg-white px-4 text-sm font-semibold text-indigo-600 shadow-soft">
          <Sparkles className="h-4 w-4" />
          AI prioritized
        </div>
      </header>

      <section className="mt-8 space-y-4">
        {recommendations.map(([title, detail, impact, savings]) => (
          <article key={title} className="flex items-center gap-5 rounded-lg border border-slate-200 bg-white p-5 shadow-soft">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
              <Lightbulb className="h-6 w-6" />
            </div>
            <div className="min-w-0 flex-1">
              <h2 className="text-base font-bold text-slate-950">{title}</h2>
              <p className="mt-1 text-sm text-slate-600">{detail}</p>
            </div>
            <div className="w-28 text-sm">
              <div className="text-slate-400">Impact</div>
              <div className="font-bold text-indigo-600">{impact}</div>
            </div>
            <div className="w-32 text-sm">
              <div className="text-slate-400">Potential Savings</div>
              <div className="font-bold text-slate-950">{savings}</div>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
