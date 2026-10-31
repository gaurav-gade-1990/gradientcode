import { Link, useParams } from "react-router";
import { IconCheck, IconChevronLeft, IconHalfCircle } from "../components/Icons";
import { PageShell } from "../components/Nav";
import { DifficultyBoxes, ProgressRing, diffText, emptyCounts } from "../components/ui";
import { resolvePlan } from "../lib/data";
import { useIndex, useProgress } from "../lib/hooks";
import { PlanGlyph } from "./StudyPlans";

export default function StudyPlanPage() {
  const { id } = useParams();
  const { index } = useIndex();
  const { solved, attempted } = useProgress();
  const i = index?.plans.findIndex((p) => p.id === id) ?? -1;
  if (!index) return <PageShell>{null}</PageShell>;
  if (i < 0)
    return (
      <PageShell>
        <p className="text-muted">
          No study plan named "{id}". <Link to="/study-plans" className="text-gc-blue">All study plans</Link>
        </p>
      </PageShell>
    );
  const plan = resolvePlan(index.plans[i], index.problems);
  const counts = emptyCounts();
  for (const p of plan.problems) {
    counts[p.difficulty].total++;
    if (solved[p.slug]) counts[p.difficulty].solved++;
  }
  const done = plan.problems.filter((p) => solved[p.slug]).length;
  const next = plan.problems.find((p) => !solved[p.slug]);
  const catName = new Map(index.categories.map((c) => [c.key, c.name]));
  return (
    <PageShell>
      <Link to="/study-plans" className="mb-4 inline-flex items-center gap-1 text-[13px] text-muted hover:text-strong">
        <IconChevronLeft size={14} /> Study Plans
      </Link>
      <div className="flex gap-6">
        <div className="min-w-0 flex-1">
          <div className="mb-6 flex items-center gap-4">
            <PlanGlyph i={i} size={72} />
            <div>
              <h1 className="text-[24px] font-semibold text-strong" data-testid="plan-title">
                {plan.title}
              </h1>
              <p className="max-w-[620px] text-[14px] text-label">{plan.description}</p>
            </div>
          </div>
          {plan.sections.map((s, si) => {
            const sd = s.problems.filter((p) => solved[p.slug]).length;
            return (
              <section key={si} className="mb-5 overflow-hidden rounded-lg bg-layer1" data-testid="plan-section">
                <div className="flex items-center justify-between border-b border-divider px-4 py-3">
                  <h2 className="text-[15px] font-semibold text-strong">
                    {si + 1}. {s.title}
                  </h2>
                  <span className="text-[12px] text-muted">
                    {sd}/{s.problems.length}
                  </span>
                </div>
                <ul>
                  {s.problems.map((p, pi) => (
                    <li key={p.slug} className={pi % 2 === 0 ? "bg-fill4" : ""}>
                      <Link to={`/problems/${p.slug}`} className="flex items-center gap-3 px-4 py-2.5 text-[14px] hover:bg-fill3">
                        <span className="flex w-5 justify-center">
                          {solved[p.slug] ? (
                            <IconCheck size={17} className="text-gc-green" />
                          ) : attempted[p.slug] ? (
                            <IconHalfCircle size={16} className="text-medium" />
                          ) : (
                            <span className="h-3.5 w-3.5 rounded-full border border-line" />
                          )}
                        </span>
                        <span className="flex-1 truncate text-strong">{p.title}</span>
                        <span className="hidden w-[200px] truncate text-[13px] text-muted md:block">{catName.get(p.category)}</span>
                        <span className={`w-14 text-right text-[13px] ${diffText[p.difficulty]}`}>{p.difficulty === "Medium" ? "Med." : p.difficulty}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
        </div>
        <aside className="hidden w-[280px] shrink-0 lg:block">
          <div className="sticky top-[74px] rounded-lg bg-layer1 p-4">
            <div className="mb-3 text-[14px] font-medium text-strong">Plan progress</div>
            <div className="flex items-center justify-between">
              <ProgressRing counts={counts} />
              <DifficultyBoxes counts={counts} />
            </div>
            <div className="mt-4 text-[13px] text-muted">
              {done === plan.problems.length && plan.problems.length > 0 ? "Plan complete." : `${plan.problems.length - done} problems to go.`}
            </div>
            {next && (
              <Link to={`/problems/${next.slug}`} className="mt-3 flex h-9 items-center justify-center truncate rounded-lg bg-gc-green px-3 text-[14px] font-medium text-white hover:bg-gc-green-hover">
                {done ? "Continue" : "Start"}: {next.title}
              </Link>
            )}
          </div>
        </aside>
      </div>
    </PageShell>
  );
}
