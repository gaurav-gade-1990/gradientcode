// Main-thread client for the Pyodide worker. It owns the wall-clock budget: a judge call that runs past
// max(8000, sum of time_limit_ms over the cases being run) terminates the worker, reports Time Limit Exceeded,
// and starts a fresh worker for the next call.
import { useSyncExternalStore } from "react";
import type { JudgeResult, Problem } from "./types";

export type EngineState = "idle" | "loading" | "ready" | "error";

const BASE = import.meta.env.BASE_URL;
const MIN_BUDGET_MS = 8000;

interface Pending {
  resolve: (r: JudgeResult) => void;
  timer: ReturnType<typeof setTimeout>;
}

class JudgeClient {
  private worker: Worker | null = null;
  private ready: Promise<void> | null = null;
  private pending = new Map<number, Pending>();
  private nextId = 1;
  private listeners = new Set<() => void>();
  state: EngineState = "idle";
  error = "";

  subscribe = (fn: () => void) => {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  };

  private setState(s: EngineState, error = "") {
    this.state = s;
    this.error = error;
    this.listeners.forEach((fn) => fn());
  }

  /** Start loading Pyodide (idempotent). */
  ensure(): Promise<void> {
    if (this.ready) return this.ready;
    this.setState("loading");
    const w = new Worker(`${BASE}pyodide-worker.js`);
    this.worker = w;
    this.ready = new Promise<void>((resolve, reject) => {
      w.onmessage = (e: MessageEvent) => {
        const msg = e.data;
        if (msg.type === "ready") {
          this.setState("ready");
          resolve();
        } else if (msg.type === "error") {
          this.setState("error", msg.error);
          this.reset();
          reject(new Error(msg.error));
        } else if (msg.type === "result") {
          const p = this.pending.get(msg.id);
          if (!p) return;
          clearTimeout(p.timer);
          this.pending.delete(msg.id);
          if (msg.error) p.resolve(internal(msg.error));
          else p.resolve(msg.result as JudgeResult);
        }
      };
      w.onerror = (e) => {
        const err = e.message || "the Python worker failed to start";
        this.setState("error", err);
        this.reset();
        reject(new Error(err));
      };
    });
    this.ready.catch(() => {});
    w.postMessage({
      type: "init",
      harnessUrl: new URL(`${BASE}harness.py`, location.href).href,
      runtimeUrl: new URL(`${BASE}gc_runtime.py`, location.href).href,
    });
    return this.ready;
  }

  private reset() {
    this.worker?.terminate();
    this.worker = null;
    this.ready = null;
    for (const [, p] of this.pending) {
      clearTimeout(p.timer);
      p.resolve(internal("the Python worker stopped"));
    }
    this.pending.clear();
  }

  async judge(problem: Problem, code: string, mode: "run" | "submit", custom: string[] = []): Promise<JudgeResult> {
    try {
      await this.ensure();
    } catch (e) {
      return internal(e instanceof Error ? e.message : String(e));
    }
    const nCases = mode === "submit" ? problem.cases.length : problem.cases.filter((c) => !c.hidden).length + custom.length;
    const limit = problem.meta.time_limit_ms ?? 5000;
    const budget = Math.max(MIN_BUDGET_MS, nCases * limit);
    const id = this.nextId++;
    const w = this.worker!;
    return new Promise<JudgeResult>((resolve) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        // Kill the stuck interpreter and warm up a new one for the next call.
        this.reset();
        this.setState("idle");
        this.ensure().catch(() => {});
        resolve({ status: "Time Limit Exceeded", passed: 0, total: nCases, runtime_ms: budget, cases: [] });
      }, budget);
      this.pending.set(id, { resolve, timer });
      w.postMessage({ type: "judge", id, problem: JSON.stringify(problem), code, mode, custom: JSON.stringify(custom) });
    });
  }
}

function internal(error: string): JudgeResult {
  return { status: "Runtime Error", passed: 0, total: 0, runtime_ms: 0, cases: [], internalError: error };
}

export const judgeClient = new JudgeClient();

export function useEngineState(): EngineState {
  return useSyncExternalStore(judgeClient.subscribe, () => judgeClient.state);
}
