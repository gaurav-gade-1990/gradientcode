import { useEffect, useRef, useState, type ReactNode } from "react";
import type { Difficulty } from "../lib/types";
import { IconCheck, IconChevronDown } from "./Icons";

export const diffText: Record<Difficulty, string> = { Easy: "text-easy", Medium: "text-medium", Hard: "text-hard" };
export const diffShort: Record<Difficulty, string> = { Easy: "Easy", Medium: "Med.", Hard: "Hard" };

export function DifficultyPill({ d }: { d: Difficulty }) {
  return <span className={`inline-flex h-6 items-center rounded-full bg-fill3 px-2.5 text-[12px] font-medium ${diffText[d]}`}>{d}</span>;
}

export function Pill({ children, onClick, active }: { children: ReactNode; onClick?: () => void; active?: boolean }) {
  return (
    <span
      onClick={onClick}
      className={`inline-flex h-6 items-center rounded-full px-2.5 text-[12px] ${active ? "bg-fill1 text-strong" : "bg-fill3 text-label"} ${onClick ? "cursor-pointer hover:bg-fill2" : ""}`}
    >
      {children}
    </span>
  );
}

export interface Option {
  value: string;
  label: ReactNode;
}

/** LeetCode-style filter dropdown. With `multi`, the value is a list. */
export function Dropdown({
  label,
  options,
  value,
  onChange,
  multi = false,
  testId,
  width = 180,
}: {
  label: string;
  options: Option[];
  value: string | string[];
  onChange: (v: string | string[]) => void;
  multi?: boolean;
  testId?: string;
  width?: number;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [open]);
  const selected = Array.isArray(value) ? value : value ? [value] : [];
  const current = !multi && selected.length ? options.find((o) => o.value === selected[0])?.label : null;
  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        data-testid={testId}
        onClick={() => setOpen((o) => !o)}
        className={`flex h-8 items-center gap-1.5 rounded-lg px-3 text-[14px] ${selected.length ? "bg-fill2 text-strong" : "bg-fill3 text-label"} hover:bg-fill2`}
      >
        <span>{current ?? label}</span>
        {multi && selected.length > 0 && <span className="rounded bg-fill1 px-1.5 text-[12px]">{selected.length}</span>}
        <IconChevronDown size={14} className="text-muted" />
      </button>
      {open && (
        <div
          className="absolute left-0 top-10 z-40 max-h-[320px] overflow-auto rounded-lg border border-line bg-layer2 p-1.5 shadow-[0_8px_24px_rgba(0,0,0,0.35)]"
          style={{ width }}
          role="listbox"
        >
          {options.map((o) => {
            const on = selected.includes(o.value);
            return (
              <button
                key={o.value}
                type="button"
                role="option"
                aria-selected={on}
                onClick={() => {
                  if (multi) onChange(on ? selected.filter((v) => v !== o.value) : [...selected, o.value]);
                  else {
                    onChange(on ? "" : o.value);
                    setOpen(false);
                  }
                }}
                className="flex w-full items-center justify-between rounded-md px-2.5 py-1.5 text-left text-[14px] text-label hover:bg-fill3"
              >
                <span className="truncate">{o.label}</span>
                {on && <IconCheck size={14} className="shrink-0 text-gc-blue" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

/** Solved/total ring split by difficulty, like LeetCode's progress widget. */
export function ProgressRing({
  counts,
  size = 120,
}: {
  counts: Record<Difficulty, { solved: number; total: number }>;
  size?: number;
}) {
  const order: Difficulty[] = ["Easy", "Medium", "Hard"];
  const total = order.reduce((a, d) => a + counts[d].total, 0);
  const solved = order.reduce((a, d) => a + counts[d].solved, 0);
  const r = size / 2 - 6;
  const c = 2 * Math.PI * r;
  const gap = total > 1 ? 6 : 0;
  const color: Record<Difficulty, string> = { Easy: "var(--easy)", Medium: "var(--medium)", Hard: "var(--hard)" };
  let offset = 0;
  const segs = order
    .filter((d) => counts[d].total > 0)
    .map((d) => {
      const len = (counts[d].total / Math.max(1, total)) * c;
      const seg = { d, start: offset, len: Math.max(0, len - gap), done: Math.max(0, len - gap) * (counts[d].solved / counts[d].total) };
      offset += len;
      return seg;
    });
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        {total === 0 && <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--fill2)" strokeWidth={5} />}
        {segs.map((s) => (
          <g key={s.d}>
            <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color[s.d]} strokeOpacity={0.22} strokeWidth={5} strokeLinecap="round" strokeDasharray={`${s.len} ${c}`} strokeDashoffset={-s.start} />
            {s.done > 0 && (
              <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color[s.d]} strokeWidth={5} strokeLinecap="round" strokeDasharray={`${s.done} ${c}`} strokeDashoffset={-s.start} />
            )}
          </g>
        ))}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div>
          <span className="text-[24px] font-semibold text-strong">{solved}</span>
          <span className="text-[13px] text-muted">/{total}</span>
        </div>
        <div className="flex items-center gap-1 text-[12px] text-muted">
          <IconCheck size={12} className="text-gc-green" />
          Solved
        </div>
      </div>
    </div>
  );
}

export function DifficultyBoxes({ counts }: { counts: Record<Difficulty, { solved: number; total: number }> }) {
  return (
    <div className="flex flex-col gap-1.5">
      {(["Easy", "Medium", "Hard"] as Difficulty[]).map((d) => (
        <div key={d} className="flex w-[92px] flex-col items-center rounded-lg bg-fill3 py-1">
          <span className={`text-[12px] font-medium ${diffText[d]}`}>{diffShort[d]}</span>
          <span className="text-[12px] font-medium text-strong">
            {counts[d].solved}
            <span className="text-muted">/{counts[d].total}</span>
          </span>
        </div>
      ))}
    </div>
  );
}

export function emptyCounts(): Record<Difficulty, { solved: number; total: number }> {
  return { Easy: { solved: 0, total: 0 }, Medium: { solved: 0, total: 0 }, Hard: { solved: 0, total: 0 } };
}

export function relTime(t: number): string {
  const s = Math.round((Date.now() - t) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} hr ago`;
  if (s < 86400 * 30) return `${Math.floor(s / 86400)} days ago`;
  return new Date(t).toLocaleDateString();
}
