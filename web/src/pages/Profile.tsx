import { useMemo } from "react";
import { Link } from "react-router";
import { IconCheck, IconFlame } from "../components/Icons";
import { PageShell } from "../components/Nav";
import { DifficultyBoxes, ProgressRing, diffText, emptyCounts, relTime } from "../components/ui";
import { useIndex, useProgress } from "../lib/hooks";
import { allSubmissions } from "../lib/storage";
import { trackOf } from "../lib/data";
import type { Difficulty } from "../lib/types";

const DAY = 86400000;
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function dayKey(t: number | Date) {
  const d = new Date(t);
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

function startOfDay(t: number) {
  const d = new Date(t);
  d.setHours(0, 0, 0, 0);
  return d;
}

function cellColor(n: number) {
  if (n <= 0) return "var(--fill2)";
  if (n === 1) return "rgba(44, 187, 93, 0.35)";
  if (n <= 3) return "rgba(44, 187, 93, 0.6)";
  if (n <= 6) return "rgba(44, 187, 93, 0.8)";
  return "#2cbb5d";
}

function Heatmap({ perDay }: { perDay: Map<string, number> }) {
  const today = startOfDay(Date.now());
  // 52 full weeks plus the current partial week, columns start on Sunday.
  const end = today.getTime();
  const firstSunday = new Date(end - (52 * 7 + today.getDay()) * DAY);
  const weeks: { date: Date; n: number; future: boolean }[][] = [];
  for (let w = 0; w < 53; w++) {
    const col = [];
    for (let d = 0; d < 7; d++) {
      const date = new Date(firstSunday.getFullYear(), firstSunday.getMonth(), firstSunday.getDate() + w * 7 + d);
      col.push({ date, n: perDay.get(dayKey(date)) ?? 0, future: date.getTime() > end });
    }
    weeks.push(col);
  }
  const cell = 11;
  const gap = 3;
  return (
    <div className="overflow-x-auto" data-testid="heatmap">
      <svg width={53 * (cell + gap) + 4} height={7 * (cell + gap) + 22}>
        {weeks.map((col, w) => {
          const first = col[0].date;
          const label = first.getDate() <= 7 ? MONTHS[first.getMonth()] : null;
          return (
            <g key={w} transform={`translate(${w * (cell + gap)}, 0)`}>
              {label && w < 52 && (
                <text x={0} y={10} fontSize={11} fill="var(--text-muted)">
                  {label}
                </text>
              )}
              {col.map((c, d) =>
                c.future ? null : (
                  <rect key={d} y={18 + d * (cell + gap)} width={cell} height={cell} rx={2} fill={cellColor(c.n)}>
                    <title>
                      {c.n} submission{c.n === 1 ? "" : "s"} on {c.date.toDateString()}
                    </title>
                  </rect>
                ),
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default function Profile() {
  const { index } = useIndex();
  const { solved } = useProgress();
  const subs = useMemo(() => allSubmissions(), [solved]); // eslint-disable-line react-hooks/exhaustive-deps
  const problems = index?.problems ?? [];
  const bySlug = new Map(problems.map((p) => [p.slug, p]));

  const counts = emptyCounts();
  for (const p of problems) {
    counts[p.difficulty].total++;
    if (solved[p.slug]) counts[p.difficulty].solved++;
  }

  const perDay = new Map<string, number>();
  for (const s of subs) perDay.set(dayKey(s.time), (perDay.get(dayKey(s.time)) ?? 0) + 1);
  const yearAgo = Date.now() - 365 * DAY;
  const yearSubs = subs.filter((s) => s.time >= yearAgo).length;
  const activeDays = Array.from(perDay.keys()).length;

  let streak = 0;
  {
    let t = startOfDay(Date.now()).getTime();
    if (!perDay.get(dayKey(t))) t -= DAY;
    while (perDay.get(dayKey(t))) {
      streak++;
      t -= DAY;
    }
  }
  let maxStreak = 0;
  {
    const days = Array.from(new Set(subs.map((s) => startOfDay(s.time).getTime()))).sort((a, b) => a - b);
    let run = 0;
    for (let i = 0; i < days.length; i++) {
      run = i > 0 && Math.round((days[i] - days[i - 1]) / DAY) === 1 ? run + 1 : 1;
      maxStreak = Math.max(maxStreak, run);
    }
  }

  const recent = subs.filter((s) => s.status === "Accepted" && bySlug.has(s.slug));
  const seen = new Set<string>();
  const recentUnique = recent.filter((s) => (seen.has(s.slug) ? false : (seen.add(s.slug), true))).slice(0, 15);

  return (
    <PageShell>
      <div className="flex flex-col gap-4 lg:flex-row">
        <aside className="w-full shrink-0 rounded-lg bg-layer1 p-5 lg:w-[280px]">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-16 w-16 items-center justify-center rounded-xl bg-fill2 text-[26px] font-semibold text-strong">∇</div>
            <div>
              <div className="text-[16px] font-semibold text-strong">You</div>
              <div className="text-[13px] text-muted">Progress is saved in this browser</div>
            </div>
          </div>
          <div className="border-t border-divider pt-4 text-[14px]">
            <div className="mb-2 flex items-center justify-between">
              <span className="flex items-center gap-2 text-label">
                <IconFlame size={15} className="text-accent" /> Current streak
              </span>
              <span className="font-medium text-strong" data-testid="streak">
                {streak} day{streak === 1 ? "" : "s"}
              </span>
            </div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-label">Max streak</span>
              <span className="font-medium text-strong">{maxStreak}</span>
            </div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-label">Submissions</span>
              <span className="font-medium text-strong">{subs.length}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-label">Solved</span>
              <span className="font-medium text-strong">{Object.keys(solved).filter((s) => bySlug.has(s)).length}</span>
            </div>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="rounded-lg bg-layer1 p-5">
              <div className="mb-3 text-[14px] font-medium text-strong">Solved Problems</div>
              <div className="flex items-center justify-around" data-testid="profile-ring">
                <ProgressRing counts={counts} size={130} />
                <DifficultyBoxes counts={counts} />
              </div>
            </div>
            <div className="rounded-lg bg-layer1 p-5">
              <div className="mb-3 text-[14px] font-medium text-strong">Categories</div>
              <div className="flex max-h-[300px] flex-col gap-2.5 overflow-y-auto pr-1">
                {(index?.categories ?? []).map((c) => {
                  const ps = problems.filter((p) => p.category === c.key);
                  if (!ps.length) return null;
                  const d = ps.filter((p) => solved[p.slug]).length;
                  return (
                    <div key={c.key}>
                      <div className="mb-1 flex justify-between text-[12px]">
                        <span className="text-label">{c.name}</span>
                        <span className="text-muted">
                          {d}/{ps.length}
                        </span>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-fill2">
                        <div className="h-full rounded-full bg-accent" style={{ width: `${(d / ps.length) * 100}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="rounded-lg bg-layer1 p-5" data-testid="track-progress">
            <div className="mb-3 text-[14px] font-medium text-strong">Tracks</div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              {(index?.tracks ?? []).map((t) => {
                const ps = problems.filter((p) => trackOf(p) === t.key);
                const d = ps.filter((p) => solved[p.slug]).length;
                return (
                  <div key={t.key} className="rounded-lg bg-fill4 p-3">
                    <div className="mb-1 flex items-baseline justify-between">
                      <span className="text-[13px] font-medium text-strong">{t.name}</span>
                      <span className="text-[12px] text-muted">
                        <span className="text-strong">{d}</span>/{ps.length}
                      </span>
                    </div>
                    <div className="mb-2 h-1.5 overflow-hidden rounded-full bg-fill2">
                      <div className="h-full rounded-full bg-gc-green" style={{ width: `${ps.length ? (d / ps.length) * 100 : 0}%` }} />
                    </div>
                    <div className="flex gap-3 text-[12px]">
                      {(["Easy", "Medium", "Hard"] as Difficulty[]).map((df) => {
                        const all = ps.filter((p) => p.difficulty === df);
                        return (
                          <span key={df} className={diffText[df]}>
                            {df === "Medium" ? "Med." : df} <span className="text-muted">{all.filter((p) => solved[p.slug]).length}/{all.length}</span>
                          </span>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="rounded-lg bg-layer1 p-5">
            <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
              <div className="text-[14px] text-label">
                <span className="text-[16px] font-semibold text-strong">{yearSubs}</span> submissions in the past one year
              </div>
              <div className="text-[13px] text-muted">
                Total active days: <span className="text-strong">{activeDays}</span> · Max streak: <span className="text-strong">{maxStreak}</span>
              </div>
            </div>
            <Heatmap perDay={perDay} />
          </div>

          <div className="rounded-lg bg-layer1 p-5">
            <div className="mb-3 flex items-center gap-2 text-[14px] font-medium text-strong">
              <IconCheck size={15} className="text-gc-green" /> Recent AC
            </div>
            {recentUnique.length === 0 ? (
              <p className="py-6 text-center text-[14px] text-muted">No accepted submissions yet.</p>
            ) : (
              <ul data-testid="recent-ac">
                {recentUnique.map((s, i) => {
                  const p = bySlug.get(s.slug)!;
                  return (
                    <li key={s.id} className={`rounded-lg ${i % 2 === 0 ? "bg-fill4" : ""}`}>
                      <Link to={`/problems/${s.slug}`} className="flex items-center justify-between rounded-lg px-4 py-3 text-[14px] hover:bg-fill3">
                        <span className="truncate text-strong">
                          {p.title} <span className={`ml-2 text-[12px] ${diffText[p.difficulty]}`}>{p.difficulty}</span>
                        </span>
                        <span className="shrink-0 text-[13px] text-muted">{relTime(s.time)}</span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      </div>
    </PageShell>
  );
}
