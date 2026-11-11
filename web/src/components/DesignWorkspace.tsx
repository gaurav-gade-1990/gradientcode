import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router";
import { Panel, PanelGroup } from "react-resizable-panels";
import { useProgress } from "../lib/hooks";
import { completeDesign, getDesignDraft, setDesignDraft, type DesignDraft } from "../lib/storage";
import type { DesignProblem, Pillar, ProblemIndex, RubricSection } from "../lib/types";
import { IconBook, IconBulb, IconCheck, IconChevronDown, IconDoc, IconList, IconPlay } from "./Icons";
import { Markdown } from "./Markdown";
import { DifficultyPill, Pill, diffText } from "./ui";
import { Gutter, PanelTabs, TopBar } from "./WorkspaceChrome";

type PillarDef = { key: Pillar; name: string };

/** Pillar names and the badge label per rubric track; the sections themselves come from rubric.json. */
const FRAMEWORKS: Record<"design" | "leadership", { label: string; pillars: PillarDef[] }> = {
  design: {
    label: "System Design",
    pillars: [
      { key: "A", name: "Scope & architecture" },
      { key: "B", name: "Agents, retrieval & processing" },
      { key: "C", name: "Data, infra & serving" },
      { key: "D", name: "Health, quality & execution" },
    ],
  },
  leadership: {
    label: "AI Leadership",
    pillars: [
      { key: "A", name: "Frame" },
      { key: "B", name: "Decide" },
      { key: "C", name: "Execute" },
      { key: "D", name: "Land" },
    ],
  },
};
const PILLAR_SECS = 5 * 60;
const PASS = 0.7;

function clock(secs: number) {
  const s = Math.max(0, Math.round(secs));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

function IconPause({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <rect x="6" y="4" width="4" height="16" rx="1" />
      <rect x="14" y="4" width="4" height="16" rx="1" />
    </svg>
  );
}

function IconLock({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" aria-hidden>
      <rect x="4" y="11" width="16" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  );
}

/** Split the model answer on its `## n. Title` headings. */
function splitSolution(md: string): Map<number, { title: string; body: string }> {
  const out = new Map<number, { title: string; body: string }>();
  const re = /^##\s+(\d+)\.\s+(.+)$/gm;
  const hits = Array.from(md.matchAll(re));
  hits.forEach((m, i) => {
    const start = (m.index ?? 0) + m[0].length;
    const end = i + 1 < hits.length ? hits[i + 1].index ?? md.length : md.length;
    out.set(Number(m[1]), { title: m[2].trim(), body: md.slice(start, end).trim() });
  });
  return out;
}

function scoreOf(sections: RubricSection[], checks: DesignDraft["checks"]) {
  let checked = 0;
  let total = 0;
  const byPillar: Record<string, { checked: number; total: number }> = {};
  for (const s of sections) {
    const c = checks[s.n] ?? [];
    const k = s.criteria.filter((_, i) => c[i]).length;
    checked += k;
    total += s.criteria.length;
    const p = (byPillar[s.pillar] ??= { checked: 0, total: 0 });
    p.checked += k;
    p.total += s.criteria.length;
  }
  return { checked, total, byPillar };
}

type Running = { total: boolean; pillar: Pillar | null };

export function DesignWorkspace({ problem, index }: { problem: DesignProblem; index: ProblemIndex | null }) {
  const { meta } = problem;
  const slug = meta.slug;
  const sections = problem.rubric.sections;
  const framework = FRAMEWORKS[meta.track === "leadership" ? "leadership" : "design"];
  // Only pillars that have sections in this rubric.
  const PILLARS = framework.pillars.filter((p) => sections.some((s) => s.pillar === p.key));
  const budgetSecs = (meta.time_minutes ?? 45) * 60;
  const { solved } = useProgress();
  const [draft, setDraft] = useState<DesignDraft>(() => getDesignDraft(slug));
  const [running, setRunning] = useState<Running>({ total: false, pillar: null });
  const [leftTab, setLeftTab] = useState<"prompt" | "answer" | "related" | "explanation">("prompt");
  const [confirming, setConfirming] = useState(false);
  const [open, setOpen] = useState<Set<number>>(() => new Set(sections.filter((s) => s.pillar === "A").map((s) => s.n)));
  const [preview, setPreview] = useState<Set<number>>(new Set());
  const [note, setNote] = useState<{ ok: boolean; text: string } | null>(null);
  const solutionRef = useRef<HTMLDivElement>(null);

  // Debounced save of the whole draft.
  useEffect(() => {
    const t = setTimeout(() => setDesignDraft(slug, draft), 300);
    return () => clearTimeout(t);
  }, [draft, slug]);

  // One ticking interval drives the total timer and the active pillar timer.
  useEffect(() => {
    if (!running.total && !running.pillar) return;
    const id = setInterval(() => {
      setDraft((d) => ({
        ...d,
        totalSecs: d.totalSecs + (running.total ? 1 : 0),
        pillarSecs: running.pillar ? { ...d.pillarSecs, [running.pillar]: (d.pillarSecs[running.pillar] ?? 0) + 1 } : d.pillarSecs,
      }));
    }, 1000);
    return () => clearInterval(id);
  }, [running]);

  const solution = useMemo(() => splitSolution(problem.solution), [problem.solution]);
  const score = scoreOf(sections, draft.checks);
  const pct = score.total ? score.checked / score.total : 0;
  const isSolved = !!solved[slug];

  const setAnswer = (n: number, text: string) => setDraft((d) => ({ ...d, answers: { ...d.answers, [n]: text } }));
  const toggleCheck = (n: number, i: number) =>
    setDraft((d) => {
      const c = [...(d.checks[n] ?? [])];
      c[i] = !c[i];
      return { ...d, checks: { ...d.checks, [n]: c } };
    });
  const toggle = (set: Set<number>, n: number) => {
    const s = new Set(set);
    if (s.has(n)) s.delete(n);
    else s.add(n);
    return s;
  };

  const reveal = () => {
    setDraft((d) => ({ ...d, revealed: true }));
    setRunning({ total: false, pillar: null });
    setConfirming(false);
    setOpen(new Set(sections.map((s) => s.n)));
  };

  const markComplete = () => {
    if (!draft.revealed) return;
    const text = sections.map((s) => `## ${s.n}. ${s.title}\n\n${draft.answers[s.n] ?? ""}`).join("\n\n");
    const sub = completeDesign(slug, score.checked, score.total, draft.totalSecs, text);
    setRunning({ total: false, pillar: null });
    if (sub.status === "Accepted") {
      setDraft((d) => ({ ...d, completedAt: d.completedAt ?? sub.time }));
      setNote({ ok: true, text: `Marked complete with ${score.checked}/${score.total} criteria (${Math.round(pct * 100)}%).` });
    } else {
      setNote({ ok: false, text: `${Math.round(pct * 100)}% of criteria checked. You need ${Math.round(PASS * 100)}% to mark this complete; it is saved as attempted.` });
    }
  };

  const center = (
    <>
      <div className="flex h-8 items-center gap-2 rounded-l-lg bg-fill3 pl-3 pr-1.5 text-[14px]" data-testid="total-timer">
        <span className={`font-mono text-[13px] ${draft.totalSecs > budgetSecs ? "text-gc-red" : "text-strong"}`}>{clock(draft.totalSecs)}</span>
        <span className="font-mono text-[13px] text-muted">/ {clock(budgetSecs)}</span>
        <button
          type="button"
          title={running.total ? "Pause timer" : "Start timer"}
          data-testid="total-timer-toggle"
          onClick={() => setRunning((r) => ({ ...r, total: !r.total }))}
          className="flex h-6 w-6 items-center justify-center rounded text-label hover:bg-fill2 hover:text-strong"
        >
          {running.total ? <IconPause size={12} /> : <IconPlay size={12} />}
        </button>
      </div>
      <button
        type="button"
        onClick={markComplete}
        disabled={!draft.revealed}
        data-testid="mark-complete"
        title={draft.revealed ? "Record this answer" : "Reveal the model answer and score yourself first"}
        className="flex h-8 items-center gap-1.5 rounded-r-lg bg-gc-green px-3 text-[14px] font-medium text-white hover:bg-gc-green-hover disabled:cursor-not-allowed disabled:opacity-50"
      >
        <IconCheck size={14} />
        Mark complete
      </button>
    </>
  );

  const builtBySlug = new Map((index?.problems ?? []).map((p) => [p.slug, p]));

  const left = (
    <div className="flex h-full flex-col overflow-hidden rounded-lg bg-layer1">
      <PanelTabs
        value={leftTab}
        onChange={setLeftTab}
        tabs={[
          { key: "prompt", label: "Prompt", icon: <IconDoc size={15} className="text-gc-blue" /> },
          { key: "answer", label: "Model Answer", icon: <IconBook size={15} className="text-accent" /> },
          { key: "related", label: "Related", icon: <IconList size={15} className="text-gc-blue" /> },
          ...(problem.walkthrough
            ? [{ key: "explanation" as const, label: "Detailed Explanation", icon: <IconBulb size={15} className="text-accent" /> }]
            : []),
        ]}
      />
      <div className="min-h-0 flex-1 overflow-y-auto" ref={solutionRef}>
        {leftTab === "prompt" && (
          <div className="px-5 pb-8 pt-4">
            <div className="mb-3 flex items-start justify-between gap-3">
              <h1 className="text-[24px] font-semibold leading-8 text-strong" data-testid="problem-title">
                {meta.id}. {meta.title}
              </h1>
              {isSolved && (
                <span className="mt-1.5 flex shrink-0 items-center gap-1 text-[13px] text-gc-green">
                  Completed <IconCheck size={14} />
                </span>
              )}
            </div>
            <div className="mb-5 flex flex-wrap gap-2">
              <DifficultyPill d={meta.difficulty} />
              <Pill>{framework.label}</Pill>
              <Pill>{meta.time_minutes ?? 45} min</Pill>
              {meta.tags.map((t) => (
                <Pill key={t}>{t}</Pill>
              ))}
            </div>
            <Markdown prose>{problem.description}</Markdown>
            <div className="mt-6 rounded-lg bg-fill3 px-4 py-3 text-[13px] leading-5 text-label">
              Answer in the panel on the right, section by section. Each pillar gets about five minutes. When you are done, reveal the model answer and score yourself against the rubric.
            </div>
          </div>
        )}
        {leftTab === "answer" &&
          (draft.revealed ? (
            <div data-testid="model-answer">
              <nav className="sticky top-0 z-10 border-b border-divider bg-layer1 px-5 py-2.5">
                <div className="flex flex-wrap gap-x-4 gap-y-1.5">
                  {PILLARS.map((p) => (
                    <div key={p.key} className="flex items-center gap-1">
                      <span className="mr-0.5 text-[12px] font-semibold text-muted">{p.key}</span>
                      {sections
                        .filter((s) => s.pillar === p.key)
                        .map((s) => (
                          <button
                            key={s.n}
                            type="button"
                            title={s.title}
                            onClick={() => document.getElementById(`sol-${s.n}`)?.scrollIntoView({ behavior: "smooth", block: "start" })}
                            className="flex h-6 min-w-6 items-center justify-center rounded-md bg-fill3 px-1.5 text-[12px] text-label hover:bg-fill2 hover:text-strong"
                          >
                            {s.n}
                          </button>
                        ))}
                    </div>
                  ))}
                </div>
              </nav>
              <div className="px-5 pb-10 pt-2">
                {PILLARS.map((p) => (
                  <section key={p.key} className="mt-4">
                    <h2 className="mb-2 border-b border-divider pb-2 text-[13px] font-semibold uppercase tracking-wide text-accent">
                      {p.key}. {p.name}
                    </h2>
                    {sections
                      .filter((s) => s.pillar === p.key)
                      .map((s) => {
                        const sol = solution.get(s.n);
                        return (
                          <div key={s.n} id={`sol-${s.n}`} className="scroll-mt-14">
                            <h3 className="mb-2 mt-5 text-[16px] font-semibold text-strong">
                              {s.n}. {sol?.title ?? s.title}
                            </h3>
                            {sol ? <Markdown prose>{sol.body}</Markdown> : <p className="text-muted">No model answer for this section.</p>}
                          </div>
                        );
                      })}
                  </section>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center px-8 py-16 text-center">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-fill3 text-muted">
                <IconLock size={20} />
              </div>
              <h2 className="mb-1 text-[16px] font-semibold text-strong">The model answer is hidden</h2>
              <p className="mb-5 max-w-[360px] text-[14px] text-muted">Write your own answer first. Revealing it pauses your timers and turns on rubric scoring.</p>
              {confirming ? (
                <div className="rounded-lg border border-line bg-layer2 p-4" data-testid="reveal-confirm">
                  <p className="mb-3 text-[14px] text-label">Reveal the model answer now? You can't hide it again.</p>
                  <div className="flex justify-center gap-2">
                    <button type="button" onClick={() => setConfirming(false)} className="h-8 rounded-lg bg-fill3 px-3 text-[14px] text-label hover:bg-fill2">
                      Cancel
                    </button>
                    <button type="button" onClick={reveal} data-testid="reveal-yes" className="h-8 rounded-lg bg-accent px-3 text-[14px] font-medium text-black hover:brightness-110">
                      Yes, reveal
                    </button>
                  </div>
                </div>
              ) : (
                <button type="button" onClick={() => setConfirming(true)} data-testid="reveal" className="h-9 rounded-lg bg-fill2 px-4 text-[14px] font-medium text-strong hover:bg-fill1">
                  Reveal model answer
                </button>
              )}
            </div>
          ))}
        {leftTab === "explanation" && problem.walkthrough && (
          <div className="px-5 pb-8 pt-4">
            <h2 className="mb-4 text-[20px] font-semibold text-strong">Detailed Explanation</h2>
            <Markdown prose>{problem.walkthrough}</Markdown>
          </div>
        )}
        {leftTab === "related" && (
          <div className="px-5 pb-8 pt-4">
            <h2 className="mb-1 text-[16px] font-semibold text-strong">Related coding problems</h2>
            <p className="mb-4 text-[13px] text-muted">Each one builds a piece of this design.</p>
            <ul className="flex flex-col" data-testid="related">
              {(meta.related ?? []).map((s, i) => {
                const p = builtBySlug.get(s);
                return (
                  <li key={s} className={`flex items-center justify-between rounded-md px-3 py-2.5 text-[14px] ${i % 2 === 0 ? "bg-fill4" : ""}`}>
                    {p ? (
                      <Link to={`/problems/${p.slug}`} className="text-strong hover:text-gc-blue">
                        {p.id}. {p.title}
                      </Link>
                    ) : (
                      <span className="text-muted">{s}</span>
                    )}
                    {p ? <span className={`text-[12px] ${diffText[p.difficulty]}`}>{p.difficulty}</span> : <span className="text-[12px] text-faint">coming soon</span>}
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </div>
    </div>
  );

  const right = (
    <div className="flex h-full flex-col overflow-hidden rounded-lg bg-layer1">
      <PanelTabs
        value="workspace"
        onChange={() => {}}
        tabs={[{ key: "workspace", label: "Your Answer", icon: <IconDoc size={15} className="text-gc-green" /> }]}
        right={
          draft.revealed ? (
            <span className="mr-2 text-[13px] text-label" data-testid="overall-score">
              Score <span className={pct >= PASS ? "font-medium text-gc-green" : "font-medium text-strong"}>{score.checked}</span>
              <span className="text-muted">
                /{score.total} · {Math.round(pct * 100)}%
              </span>
            </span>
          ) : (
            <span className="mr-2 text-[12px] text-muted">Saved in this browser</span>
          )
        }
      />
      <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-8 pt-3" data-testid="design-answer">
        {note && (
          <div className={`mb-3 rounded-lg px-3 py-2 text-[13px] ${note.ok ? "bg-gc-green/10 text-gc-green" : "bg-err text-gc-red"}`} data-testid="complete-note">
            {note.text}
          </div>
        )}
        {PILLARS.map((p) => {
          const used = draft.pillarSecs[p.key] ?? 0;
          const left_ = PILLAR_SECS - used;
          const on = running.pillar === p.key;
          const ps = score.byPillar[p.key];
          return (
            <section key={p.key} className="mb-4" data-testid={`pillar-${p.key}`}>
              <div className="mb-2 flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-md bg-accent/15 text-[12px] font-semibold text-accent">{p.key}</span>
                <h2 className="text-[14px] font-semibold text-strong">{p.name}</h2>
                {draft.revealed && ps && (
                  <span className="text-[12px] text-muted" data-testid={`pillar-score-${p.key}`}>
                    {ps.checked}/{ps.total}
                  </span>
                )}
                <div className="ml-auto flex items-center gap-1 rounded-md bg-fill3 pl-2 pr-0.5">
                  <span className={`font-mono text-[12px] ${left_ < 0 ? "text-gc-red" : on ? "text-strong" : "text-label"}`}>
                    {left_ < 0 ? "+" : ""}
                    {clock(Math.abs(left_))}
                  </span>
                  <button
                    type="button"
                    title={on ? "Pause pillar timer" : "Start pillar timer (5 min)"}
                    data-testid={`pillar-timer-${p.key}`}
                    onClick={() => setRunning((r) => ({ total: on ? r.total : true, pillar: on ? null : p.key }))}
                    className="flex h-6 w-6 items-center justify-center rounded text-label hover:bg-fill2 hover:text-strong"
                  >
                    {on ? <IconPause size={11} /> : <IconPlay size={11} />}
                  </button>
                </div>
              </div>
              <div className="flex flex-col gap-2">
                {sections
                  .filter((s) => s.pillar === p.key)
                  .map((s) => (
                    <SectionCard
                      key={s.n}
                      s={s}
                      open={open.has(s.n)}
                      onToggle={() => setOpen((o) => toggle(o, s.n))}
                      preview={preview.has(s.n)}
                      onPreview={() => setPreview((o) => toggle(o, s.n))}
                      value={draft.answers[s.n] ?? ""}
                      onChange={(v) => setAnswer(s.n, v)}
                      revealed={draft.revealed}
                      checks={draft.checks[s.n] ?? []}
                      onCheck={(i) => toggleCheck(s.n, i)}
                    />
                  ))}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );

  return (
    <>
      <TopBar index={index} slug={slug} center={center} />
      <div className="min-h-0 flex-1 px-2 pb-2">
        <PanelGroup direction="horizontal" autoSaveId="gc:layout:design">
          <Panel defaultSize={45} minSize={20}>
            {left}
          </Panel>
          <Gutter />
          <Panel defaultSize={55} minSize={25}>
            {right}
          </Panel>
        </PanelGroup>
      </div>
    </>
  );
}

function SectionCard({
  s,
  open,
  onToggle,
  preview,
  onPreview,
  value,
  onChange,
  revealed,
  checks,
  onCheck,
}: {
  s: RubricSection;
  open: boolean;
  onToggle: () => void;
  preview: boolean;
  onPreview: () => void;
  value: string;
  onChange: (v: string) => void;
  revealed: boolean;
  checks: boolean[];
  onCheck: (i: number) => void;
}): ReactNode {
  const done = s.criteria.filter((_, i) => checks[i]).length;
  const words = value.trim() ? value.trim().split(/\s+/).length : 0;
  return (
    <div className="rounded-lg border border-divider bg-fill4" data-testid={`section-${s.n}`}>
      <button type="button" onClick={onToggle} className="flex w-full items-center gap-2 px-3 py-2.5 text-left" data-testid={`section-toggle-${s.n}`}>
        <span className="text-[14px] font-medium text-strong">
          {s.n}. {s.title}
        </span>
        {!open && value.trim() && <IconCheck size={13} className="text-gc-green" />}
        <span className="ml-auto flex items-center gap-2">
          {revealed && (
            <span className={`text-[12px] ${done === s.criteria.length ? "text-gc-green" : "text-muted"}`}>
              {done}/{s.criteria.length}
            </span>
          )}
          <IconChevronDown size={15} className={`text-muted transition-transform ${open ? "rotate-180" : ""}`} />
        </span>
      </button>
      {open && (
        <div className="px-3 pb-3">
          {preview ? (
            <div className="min-h-[96px] rounded-lg bg-fill3 px-3 py-2">{value.trim() ? <Markdown prose>{value}</Markdown> : <p className="text-[13px] text-muted">Nothing written yet.</p>}</div>
          ) : (
            <textarea
              data-testid={`answer-${s.n}`}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              placeholder={s.prompt}
              spellCheck
              rows={Math.min(14, Math.max(4, value.split("\n").length + 1))}
              className="w-full resize-y rounded-lg border border-transparent bg-fill3 px-3 py-2 text-[14px] leading-[22px] text-strong placeholder:text-muted outline-none focus:border-line"
            />
          )}
          <div className="mt-1 flex items-center justify-between text-[12px] text-muted">
            <span>Markdown · {words} words</span>
            <button type="button" onClick={onPreview} className="rounded px-1.5 py-0.5 hover:bg-fill3 hover:text-strong">
              {preview ? "Edit" : "Preview"}
            </button>
          </div>
          {revealed && (
            <div className="mt-3 border-t border-divider pt-2.5">
              <div className="mb-1.5 text-[12px] font-medium text-muted">Rubric: check what your answer covered</div>
              <ul className="flex flex-col gap-1">
                {s.criteria.map((c, i) => (
                  <li key={i}>
                    <label className="flex cursor-pointer items-start gap-2 rounded-md px-1 py-1 text-[13px] leading-5 text-label hover:bg-fill3">
                      <input type="checkbox" checked={!!checks[i]} onChange={() => onCheck(i)} className="mt-0.5 h-4 w-4 shrink-0 accent-[#2cbb5d]" data-testid={`criterion-${s.n}-${i}`} />
                      <span className={checks[i] ? "text-strong" : ""}>{c}</span>
                    </label>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
