import { useEffect, useState, useSyncExternalStore } from "react";
import { loadIndex } from "./data";
import { getAttempted, getSolved, getTheme, PROGRESS_EVENT } from "./storage";
import type { ProblemIndex } from "./types";

export function useIndex(): { index: ProblemIndex | null; error: string } {
  const [index, setIndex] = useState<ProblemIndex | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let live = true;
    loadIndex()
      .then((i) => live && setIndex(i))
      .catch((e) => live && setError(String(e.message ?? e)));
    return () => {
      live = false;
    };
  }, []);
  return { index, error };
}

let progressVersion = 0;
function subscribeProgress(fn: () => void) {
  const h = () => {
    progressVersion++;
    fn();
  };
  window.addEventListener(PROGRESS_EVENT, h);
  window.addEventListener("storage", h);
  return () => {
    window.removeEventListener(PROGRESS_EVENT, h);
    window.removeEventListener("storage", h);
  };
}

/** Re-renders when progress changes; returns the current solved and attempted maps. */
export function useProgress() {
  const v = useSyncExternalStore(subscribeProgress, () => progressVersion);
  const [state, setState] = useState(() => ({ solved: getSolved(), attempted: getAttempted() }));
  useEffect(() => {
    setState({ solved: getSolved(), attempted: getAttempted() });
  }, [v]);
  return state;
}

function subscribeTheme(fn: () => void) {
  window.addEventListener("gc-theme", fn);
  return () => window.removeEventListener("gc-theme", fn);
}

export function useTheme(): "dark" | "light" {
  return useSyncExternalStore(subscribeTheme, getTheme);
}
