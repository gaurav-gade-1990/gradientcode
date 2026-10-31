import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router";
import { IconCheck, IconHalfCircle, IconSearch, IconShuffle, IconX } from "../components/Icons";
import { PageShell } from "../components/Nav";
import { DifficultyBoxes, Dropdown, ProgressRing, diffText, emptyCounts } from "../components/ui";
import { useIndex, useProgress } from "../lib/hooks";
import { trackOf } from "../lib/data";
import { getTrackPref, setTrackPref, statusOf } from "../lib/storage";
import type { Difficulty, TrackKey } from "../lib/types";

export default function ProblemList() {
  const { index, error } = useIndex();
  const { solved, attempted } = useProgress();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [track, setTrackState] = useState<TrackKey>(() => {
    const t = getTrackPref();
    return t === "ml" || t === "design" || t === "applied" ? t : "applied";
  });
  const setTrack = (t: TrackKey) => {
    setTrackState(t);
    setTrackPref(t);
    setCategory("");
    setTags([]);
  };

  const problems = useMemo(() => (index?.problems ?? []).filter((p) => trackOf(p) === track), [index, track]);
  const trackCategories = useMemo(() => (index?.categories ?? []).filter((c) => (c.track ?? "ml") === track), [index, track]);
  const trackCount = (t: TrackKey) => (index?.problems ?? []).filter((p) => trackOf(p) === t).length;
  const catName = useMemo(() => new Map(index?.categories.map((c) => [c.key, c.name]) ?? []), [index]);
  const allTags = useMemo(() => Array.from(new Set(problems.flatMap((p) => p.tags))).sort(), [problems]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return problems.filter((p) => {
      if (needle && !`${p.id}. ${p.title} ${p.slug} ${p.tags.join(" ")}`.toLowerCase().includes(needle)) return false;
      if (difficulty && p.difficulty !== difficulty) return false;
      if (category && p.category !== category) return false;
      if (status && statusOf(p.slug, solved, attempted) !== status) return false;
      if (tags.length && !tags.every((t) => p.tags.includes(t))) return false;
      return true;
    });
  }, [problems, q, difficulty, category, status, tags, solved, attempted]);

  const counts = useMemo(() => {
    const c = emptyCounts();
    for (const p of problems) {
      c[p.difficulty].total++;
      if (solved[p.slug]) c[p.difficulty].solved++;
    }
    return c;
  }, [problems, solved]);

  const catCounts = useMemo(() => {
    const m = new Map<string, number>();
    for (const p of problems) m.set(p.category, (m.get(p.category) ?? 0) + 1);
    return m;
  }, [problems]);

  const anyFilter = q || difficulty || category || status || tags.length;
  const pickOne = () => {
    const pool = filtered.length ? filtered : problems;
    if (pool.length) navigate(`/problems/${pool[Math.floor(Math.random() * pool.length)].slug}`);
  };

  return (
    <PageShell>
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="flex rounded-lg bg-fill3 p-1" role="tablist" data-testid="track-switcher">
          {(index?.tracks ?? []).map((t) => (
            <button
              key={t.key}
              type="button"
              role="tab"
              aria-selected={track === t.key}
              data-testid={`track-${t.key}`}
              onClick={() => setTrack(t.key)}
              className={`flex h-8 items-center gap-2 rounded-md px-4 text-[14px] transition-colors ${
                track === t.key ? "bg-layer1 font-medium text-strong shadow-[0_1px_3px_rgba(0,0,0,0.25)]" : "text-muted hover:text-label"
              }`}
            >
              {t.name}
              <span className={`text-[12px] ${track === t.key ? "text-muted" : "text-faint"}`}>{trackCount(t.key)}</span>
            </button>
          ))}
        </div>
      </div>
      <div className="flex gap-6">
        <section className="min-w-0 flex-1">
          {/* category chips across the top, as on the problemset page */}
          <div className="mb-4 flex flex-wrap gap-x-5 gap-y-2 text-[14px]">
            {trackCategories
              .filter((c) => catCounts.get(c.key))
              .map((c) => (
                <button
                  key={c.key}
                  type="button"
                  onClick={() => setCategory(category === c.key ? "" : c.key)}
                  className={`flex items-center gap-1.5 ${category === c.key ? "text-accent" : "text-label hover:text-strong"}`}
                >
                  {c.name}
                  <span className="rounded-full bg-fill3 px-1.5 text-[12px] text-muted">{catCounts.get(c.key)}</span>
                </button>
              ))}
          </div>

          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Dropdown
              label="Difficulty"
              testId="filter-difficulty"
              width={140}
              value={difficulty}
              onChange={(v) => setDifficulty(v as string)}
              options={(["Easy", "Medium", "Hard"] as Difficulty[]).map((d) => ({ value: d, label: <span className={diffText[d]}>{d}</span> }))}
            />
            <Dropdown
              label="Category"
              testId="filter-category"
              width={260}
              value={category}
              onChange={(v) => setCategory(v as string)}
              options={trackCategories.map((c) => ({ value: c.key, label: c.name }))}
            />
            <Dropdown
              label="Status"
              testId="filter-status"
              width={150}
              value={status}
              onChange={(v) => setStatus(v as string)}
              options={[
                { value: "todo", label: "Todo" },
                { value: "solved", label: "Solved" },
                { value: "attempted", label: "Attempted" },
              ]}
            />
            <Dropdown label="Tags" testId="filter-tags" width={240} multi value={tags} onChange={(v) => setTags(v as string[])} options={allTags.map((t) => ({ value: t, label: t }))} />
            <div className="relative ml-1 min-w-[180px] flex-1">
              <IconSearch size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
              <input
                data-testid="search"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search questions"
                className="h-8 w-full rounded-lg bg-fill3 pl-9 pr-3 text-[14px] text-strong placeholder:text-muted outline-none focus:bg-fill2"
              />
            </div>
            <button type="button" onClick={pickOne} className="flex h-8 items-center gap-1.5 rounded-lg px-2 text-[14px] text-gc-green hover:bg-fill3" data-testid="pick-one">
              <IconShuffle size={16} />
              Pick One
            </button>
          </div>

          {anyFilter ? (
            <div className="mb-3 flex flex-wrap items-center gap-2 text-[13px] text-muted">
              <span>
                {filtered.length} of {problems.length} problems
              </span>
              <button
                type="button"
                className="flex items-center gap-1 rounded-md px-1.5 py-0.5 hover:bg-fill3 hover:text-strong"
                onClick={() => {
                  setQ("");
                  setDifficulty("");
                  setCategory("");
                  setStatus("");
                  setTags([]);
                }}
              >
                <IconX size={12} />
                Reset
              </button>
            </div>
          ) : null}

          <div className="overflow-hidden">
            <table className="w-full table-fixed border-collapse text-[14px]" data-testid="problem-table">
              <colgroup>
                <col style={{ width: 64 }} />
                <col />
                <col style={{ width: 190 }} />
                <col style={{ width: 92 }} />
                <col style={{ width: 200 }} />
              </colgroup>
              <thead>
                <tr className="border-b border-divider text-left text-[13px] text-muted">
                  <th className="px-3 py-2.5 font-normal">Status</th>
                  <th className="px-3 py-2.5 font-normal">Title</th>
                  <th className="px-3 py-2.5 font-normal">Category</th>
                  <th className="px-3 py-2.5 font-normal">Difficulty</th>
                  <th className="px-3 py-2.5 font-normal">Tags</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((p, i) => {
                  const st = statusOf(p.slug, solved, attempted);
                  return (
                    <tr key={p.slug} data-testid="problem-row" className={`${i % 2 === 0 ? "bg-fill4" : ""} hover:bg-fill3`}>
                      <td className="px-3 py-[11px]">
                        {st === "solved" ? (
                          <IconCheck size={18} className="text-gc-green" aria-label="Solved" />
                        ) : st === "attempted" ? (
                          <IconHalfCircle size={18} className="text-medium" aria-label="Attempted" />
                        ) : null}
                      </td>
                      <td className="truncate px-3 py-[11px]">
                        <Link to={`/problems/${p.slug}`} className="text-strong hover:text-gc-blue">
                          {p.id}. {p.title}
                        </Link>
                      </td>
                      <td className="truncate px-3 py-[11px] text-label">{catName.get(p.category) ?? p.category}</td>
                      <td className={`px-3 py-[11px] ${diffText[p.difficulty]}`}>{p.difficulty === "Medium" ? "Med." : p.difficulty}</td>
                      <td className="px-3 py-[11px]">
                        <div className="flex gap-1 overflow-hidden">
                          {p.tags.slice(0, 2).map((t) => (
                            <span key={t} title={t} className="max-w-[84px] shrink-0 truncate rounded-full bg-fill3 px-2 py-0.5 text-[12px] text-label">
                              {t}
                            </span>
                          ))}
                          {p.tags.length > 2 && <span className="shrink-0 px-1 text-[12px] text-muted">+{p.tags.length - 2}</span>}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {error && <p className="py-8 text-center text-gc-red">Could not load problems: {error}</p>}
            {index && problems.length === 0 && <p className="py-10 text-center text-muted">Problems for this track are on the way.</p>}
            {index && problems.length > 0 && filtered.length === 0 && <p className="py-10 text-center text-muted">No problems match these filters.</p>}
          </div>
        </section>

        <aside className="hidden w-[280px] shrink-0 lg:block">
          <div className="rounded-lg bg-layer1 p-4">
            <div className="mb-3 text-[14px] font-medium text-strong">{index?.tracks.find((t) => t.key === track)?.name ?? "Progress"}</div>
            <div className="flex items-center justify-between" data-testid="progress-ring">
              <ProgressRing counts={counts} />
              <DifficultyBoxes counts={counts} />
            </div>
          </div>
          <div className="mt-4 rounded-lg bg-layer1 p-4">
            <div className="mb-3 text-[14px] font-medium text-strong">Categories</div>
            <div className="flex flex-wrap gap-2">
              {trackCategories.map((c) => {
                const n = catCounts.get(c.key) ?? 0;
                return (
                  <button
                    key={c.key}
                    type="button"
                    disabled={!n}
                    data-testid={`chip-${c.key}`}
                    onClick={() => setCategory(category === c.key ? "" : c.key)}
                    className={`flex h-7 items-center gap-1.5 rounded-full px-3 text-[12px] disabled:opacity-40 ${
                      category === c.key ? "bg-accent text-black" : "bg-fill3 text-label hover:bg-fill2"
                    }`}
                  >
                    {c.name}
                    <span className={category === c.key ? "text-black/60" : "text-muted"}>{n}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </aside>
      </div>
    </PageShell>
  );
}
