// All progress lives in localStorage. Every read and write is wrapped: private windows and full quotas must not break the page.
import type { Status, Submission } from "./types";

const SUBS_CAP = 30;
export const PROGRESS_EVENT = "gc-progress";

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw === null ? fallback : (JSON.parse(raw) as T);
  } catch {
    return fallback;
  }
}

function write(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage unavailable */
  }
}

function notify() {
  try {
    window.dispatchEvent(new Event(PROGRESS_EVENT));
  } catch {
    /* ignore */
  }
}

export function getDraft(slug: string): string | null {
  const d = read<string | null>(`gc:drafts:${slug}`, null);
  return typeof d === "string" ? d : null;
}

export function setDraft(slug: string, code: string) {
  write(`gc:drafts:${slug}`, code);
}

export function clearDraft(slug: string) {
  try {
    localStorage.removeItem(`gc:drafts:${slug}`);
  } catch {
    /* ignore */
  }
}

export function getSubs(slug: string): Submission[] {
  const s = read<Submission[]>(`gc:subs:${slug}`, []);
  return Array.isArray(s) ? s : [];
}

export function getSolved(): Record<string, number> {
  const s = read<Record<string, number>>("gc:solved", {});
  return s && typeof s === "object" ? s : {};
}

export function getAttempted(): Record<string, number> {
  const s = read<Record<string, number>>("gc:attempted", {});
  return s && typeof s === "object" ? s : {};
}

export function addSubmission(slug: string, sub: Omit<Submission, "id" | "slug" | "time">): Submission {
  const full: Submission = { ...sub, slug, id: Math.random().toString(36).slice(2, 10), time: Date.now() };
  write(`gc:subs:${slug}`, [full, ...getSubs(slug)].slice(0, SUBS_CAP));
  if (sub.status === "Accepted") {
    const solved = getSolved();
    if (!solved[slug]) {
      solved[slug] = full.time;
      write("gc:solved", solved);
    }
  } else {
    const att = getAttempted();
    if (!att[slug]) {
      att[slug] = full.time;
      write("gc:attempted", att);
    }
  }
  notify();
  return full;
}

/** Every stored submission across problems, newest first. */
export function allSubmissions(): Submission[] {
  const out: Submission[] = [];
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith("gc:subs:")) out.push(...getSubs(key.slice("gc:subs:".length)));
    }
  } catch {
    /* ignore */
  }
  return out.sort((a, b) => b.time - a.time);
}

export type ProgressState = "solved" | "attempted" | "todo";

export function statusOf(slug: string, solved = getSolved(), attempted = getAttempted()): ProgressState {
  if (solved[slug]) return "solved";
  if (attempted[slug]) return "attempted";
  return "todo";
}

export function statusColor(status: Status | string): string {
  if (status === "Accepted" || status === "Finished") return "text-gc-green";
  return "text-gc-red";
}

export function getTheme(): "dark" | "light" {
  try {
    return localStorage.getItem("gc:theme") === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

export function setTheme(t: "dark" | "light") {
  try {
    localStorage.setItem("gc:theme", t);
  } catch {
    /* ignore */
  }
  document.documentElement.setAttribute("data-theme", t);
  window.dispatchEvent(new Event("gc-theme"));
}

// ------------------------------------------------------------ tracks and design answers

export function getTrackPref(): string | null {
  try {
    return localStorage.getItem("gc:track");
  } catch {
    return null;
  }
}

export function setTrackPref(t: string) {
  try {
    localStorage.setItem("gc:track", t);
  } catch {
    /* ignore */
  }
}

export interface DesignDraft {
  answers: Record<number, string>;
  checks: Record<number, boolean[]>;
  revealed: boolean;
  /** Seconds used per pillar timer, and on the total timer. */
  pillarSecs: Record<string, number>;
  totalSecs: number;
  completedAt?: number;
}

export function emptyDesignDraft(): DesignDraft {
  return { answers: {}, checks: {}, revealed: false, pillarSecs: {}, totalSecs: 0 };
}

export function getDesignDraft(slug: string): DesignDraft {
  const d = read<Partial<DesignDraft> | null>(`gc:design:${slug}`, null);
  if (!d || typeof d !== "object") return emptyDesignDraft();
  return { ...emptyDesignDraft(), ...d };
}

export function setDesignDraft(slug: string, d: DesignDraft) {
  write(`gc:design:${slug}`, d);
}

/** Record a self-scored design answer: solved at >= 70% of criteria, otherwise attempted. */
export function completeDesign(slug: string, checked: number, total: number, seconds: number, answerText: string): Submission {
  const ok = total > 0 && checked / total >= 0.7;
  const sub = addSubmission(slug, {
    status: ok ? "Accepted" : "Wrong Answer",
    runtime_ms: seconds * 1000,
    passed: checked,
    total,
    code: answerText,
    kind: "design",
  });
  return sub;
}
