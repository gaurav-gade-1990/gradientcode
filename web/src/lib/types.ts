export type Difficulty = "Easy" | "Medium" | "Hard";

export type TrackKey = "applied" | "ml" | "design";

export interface Track {
  key: TrackKey;
  name: string;
}

export interface Category {
  key: string;
  name: string;
  track?: TrackKey;
}

export interface ProblemSummary {
  id: number;
  slug: string;
  title: string;
  difficulty: Difficulty;
  category: string;
  tags: string[];
  track?: TrackKey;
  type?: "code" | "design";
}

export interface PlanSection {
  title: string;
  slugs: string[];
}

export interface StudyPlan {
  id: string;
  title: string;
  description: string;
  sections: PlanSection[];
}

export interface ProblemIndex {
  tracks: Track[];
  categories: Category[];
  problems: ProblemSummary[];
  plans: StudyPlan[];
}

export interface ProblemMeta extends ProblemSummary {
  mode: "function" | "driver";
  entry: string;
  signature: string;
  compare?: { rtol?: number; atol?: number };
  time_limit_ms?: number;
  hints?: string[];
  related?: string[];
  time_minutes?: number;
}

export interface Case {
  name: string;
  hidden: boolean;
  /** Encoded dict: {__dict__: [[name, value], ...]} */
  args: unknown;
  expected: unknown;
  explanation?: string;
}

export interface Problem {
  meta: ProblemMeta;
  description: string;
  editorial: string;
  /** Long-form step-by-step explanation (walkthrough.md); null until one is written. */
  walkthrough: string | null;
  starter: string;
  driver: string | null;
  checker: string | null;
  cases: Case[];
}

export type Status =
  | "Accepted"
  | "Wrong Answer"
  | "Runtime Error"
  | "Compile Error"
  | "Time Limit Exceeded"
  | "Finished";

export interface CaseResult {
  name: string;
  hidden: boolean;
  status: Status;
  input: string;
  output?: string;
  expected?: string;
  message?: string;
  error?: string;
  stdout?: string;
  ms?: number;
}

export interface JudgeResult {
  status: Status;
  passed: number;
  total: number;
  runtime_ms: number;
  cases: CaseResult[];
  /** Set by the client when the worker crashed or the page could not reach Python. */
  internalError?: string;
}

export interface Submission {
  id: string;
  slug: string;
  status: Status;
  runtime_ms: number;
  passed: number;
  total: number;
  time: number;
  code: string;
  /** "design" for a self-scored design answer marked complete. */
  kind?: "code" | "design";
}

export type Pillar = "A" | "B" | "C" | "D";

export interface RubricSection {
  n: number;
  pillar: Pillar;
  title: string;
  prompt: string;
  criteria: string[];
}

export interface DesignProblem {
  meta: ProblemMeta;
  description: string;
  rubric: { sections: RubricSection[] };
  solution: string;
  /** How to reason to the model answer (walkthrough.md). */
  walkthrough: string | null;
}

export function isDesign(p: Problem | DesignProblem): p is DesignProblem {
  return p.meta.type === "design" || "rubric" in p;
}
