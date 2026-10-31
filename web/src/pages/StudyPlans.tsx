import { Link } from "react-router";
import { PageShell } from "../components/Nav";
import { resolvePlan } from "../lib/data";
import { useIndex, useProgress } from "../lib/hooks";

const ACCENTS = ["from-[#ffa116] to-[#ff6a3d]", "from-[#2cbb5d] to-[#00b8a3]", "from-[#0a84ff] to-[#8b5cf6]"];

export function PlanGlyph({ i, size = 56 }: { i: number; size?: number }) {
  return (
    <div className={`flex shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${ACCENTS[i % ACCENTS.length]}`} style={{ width: size, height: size }}>
      <svg width={size * 0.55} height={size * 0.55} viewBox="0 0 32 32" aria-hidden>
        <path d="M4 6c3.5 0 5 17 12 17s7.5-10 12-10" fill="none" stroke="white" strokeWidth="3.2" strokeLinecap="round" />
        <circle cx="16" cy="23" r="3.2" fill="white" />
      </svg>
    </div>
  );
}

export default function StudyPlans() {
  const { index } = useIndex();
  const { solved } = useProgress();
  const plans = (index?.plans ?? []).map((p) => resolvePlan(p, index?.problems ?? []));
  return (
    <PageShell>
      <h1 className="mb-1 text-[24px] font-semibold text-strong">Study Plans</h1>
      <p className="mb-6 text-[14px] text-muted">Ordered problem sets. Work through them top to bottom.</p>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {plans.map((p, i) => {
          const done = p.problems.filter((x) => solved[x.slug]).length;
          const pct = p.problems.length ? Math.round((done / p.problems.length) * 100) : 0;
          return (
            <Link key={p.id} to={`/study-plans/${p.id}`} className="group flex flex-col rounded-xl bg-layer1 p-5 transition-colors hover:bg-layer3" data-testid="plan-card">
              <div className="mb-4 flex items-center gap-4">
                <PlanGlyph i={i} />
                <div className="min-w-0">
                  <div className="text-[16px] font-semibold text-strong group-hover:text-accent">{p.title}</div>
                  <div className="text-[13px] text-muted">
                    {p.problems.length} problems · {p.sections.length} sections
                  </div>
                </div>
              </div>
              <p className="mb-4 flex-1 text-[14px] leading-[22px] text-label">{p.description}</p>
              <div className="flex items-center gap-3">
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-fill2">
                  <div className="h-full rounded-full bg-gc-green" style={{ width: `${pct}%` }} />
                </div>
                <span className="text-[12px] text-muted">
                  {done}/{p.problems.length}
                </span>
              </div>
            </Link>
          );
        })}
      </div>
      {index && plans.length === 0 && <p className="text-muted">No study plans yet.</p>}
    </PageShell>
  );
}
