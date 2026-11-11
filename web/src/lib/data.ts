import type { DesignProblem, Problem, ProblemIndex, ProblemSummary, StudyPlan, TrackKey } from "./types";

const BASE = import.meta.env.BASE_URL;

let indexPromise: Promise<ProblemIndex> | null = null;
const problemCache = new Map<string, Promise<Problem | DesignProblem>>();

export function loadIndex(): Promise<ProblemIndex> {
  if (!indexPromise) {
    indexPromise = fetch(`${BASE}problems/index.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`index.json: HTTP ${r.status}`);
        return r.json() as Promise<ProblemIndex>;
      })
      .then((idx) => normalizeIndex(idx))
      .catch((e) => {
        indexPromise = null;
        throw e;
      });
  }
  return indexPromise;
}

export function loadProblem(slug: string): Promise<Problem | DesignProblem> {
  let p = problemCache.get(slug);
  if (!p) {
    p = fetch(`${BASE}problems/${slug}.json`).then((r) => {
      if (!r.ok) throw new Error(`Problem "${slug}" not found`);
      return r.json() as Promise<Problem | DesignProblem>;
    });
    p.catch(() => problemCache.delete(slug));
    problemCache.set(slug, p);
  }
  return p;
}

/** A plan with its unbuilt slugs dropped (and sections left empty removed). */
export function resolvePlan(plan: StudyPlan, problems: ProblemSummary[]) {
  const bySlug = new Map(problems.map((p) => [p.slug, p]));
  const sections = plan.sections
    .map((s) => ({ title: s.title, problems: s.slugs.map((slug) => bySlug.get(slug)).filter((p): p is ProblemSummary => !!p) }))
    .filter((s) => s.problems.length > 0);
  const all = Array.from(new Map(sections.flatMap((s) => s.problems).map((p) => [p.slug, p])).values());
  return { ...plan, sections, problems: all };
}

const DEFAULT_TRACKS: ProblemIndex["tracks"] = [
  { key: "applied", name: "Applied AI Engineering" },
  { key: "ml", name: "ML Foundations" },
  { key: "design", name: "System Design" },
  { key: "leadership", name: "AI Leadership" },
];

/** Fallback when an index entry has no track: the id ranges 1-99, 101-199, 201-299 and 301-399. */
function trackForId(id: number): TrackKey {
  return id >= 300 ? "leadership" : id >= 200 ? "design" : id > 100 ? "applied" : "ml";
}

/** Tracks whose problems are self-scored rubric answers rather than judged code. */
export const RUBRIC_TRACKS: TrackKey[] = ["design", "leadership"];

/** Fill in track/type for indexes built before tracks existed, and sort by id. */
export function normalizeIndex(idx: ProblemIndex): ProblemIndex {
  const tracks = idx.tracks?.length ? idx.tracks : DEFAULT_TRACKS;
  const catTrack = new Map(idx.categories.map((c) => [c.key, c.track]));
  const categories = idx.categories.map((c) => ({ ...c, track: c.track ?? "ml" }));
  const problems = [...idx.problems]
    .map((p) => {
      const track = p.track ?? catTrack.get(p.category) ?? trackForId(p.id);
      return { ...p, track, type: p.type ?? (RUBRIC_TRACKS.includes(track) ? "design" : "code") } as ProblemSummary;
    })
    .sort((a, b) => a.id - b.id);
  return { ...idx, tracks, categories, problems, plans: idx.plans ?? [] };
}

export function trackOf(p: ProblemSummary): TrackKey {
  return p.track ?? trackForId(p.id);
}
