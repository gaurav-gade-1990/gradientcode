import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router";
import { PanelResizeHandle } from "react-resizable-panels";
import type { ProblemIndex } from "../lib/types";
import { IconChevronLeft, IconChevronRight, IconList, IconShuffle } from "./Icons";
import { Logo } from "./Logo";
import { SolvedCounter, ThemeToggle } from "./Nav";

export function TopBar({ index, slug, center }: { index: ProblemIndex | null; slug: string; center: ReactNode }) {
  const navigate = useNavigate();
  // Prev/next/random stay inside the current problem's track.
  const all = index?.problems ?? [];
  const cur = all.find((p) => p.slug === slug);
  const list = cur?.track ? all.filter((p) => p.track === cur.track) : all;
  const pos = list.findIndex((p) => p.slug === slug);
  const go = (i: number) => list[i] && navigate(`/problems/${list[i].slug}`);
  const btn = "flex h-8 w-8 items-center justify-center rounded-md text-muted hover:bg-fill3 hover:text-strong disabled:opacity-30 disabled:hover:bg-transparent";
  return (
    <header className="grid h-12 shrink-0 grid-cols-[1fr_auto_1fr] items-center px-3">
      <div className="flex min-w-0 items-center gap-1">
        <div className="mr-2">
          <Logo compact />
        </div>
        <Link to="/problemset" className="flex h-8 items-center gap-2 rounded-md px-2 text-[14px] font-medium text-label hover:bg-fill3 hover:text-strong" data-testid="problem-list-link">
          <IconList size={16} />
          Problem List
        </Link>
        <button type="button" className={btn} title="Previous question" disabled={pos <= 0} onClick={() => go(pos - 1)} data-testid="prev-problem">
          <IconChevronLeft size={18} />
        </button>
        <button type="button" className={btn} title="Next question" disabled={pos < 0 || pos >= list.length - 1} onClick={() => go(pos + 1)} data-testid="next-problem">
          <IconChevronRight size={18} />
        </button>
        <button
          type="button"
          className={btn}
          title="Pick a random question"
          disabled={list.length < 2}
          onClick={() => {
            const others = list.filter((p) => p.slug !== slug);
            if (others.length) navigate(`/problems/${others[Math.floor(Math.random() * others.length)].slug}`);
          }}
        >
          <IconShuffle size={16} />
        </button>
      </div>
      <div className="flex items-center gap-1">{center}</div>
      <div className="flex items-center justify-end gap-2">
        <Link to="/study-plans" className="hidden h-8 items-center rounded-md px-2 text-[14px] text-muted hover:bg-fill3 hover:text-strong md:flex">
          Study Plans
        </Link>
        <Link to="/profile" className="hidden h-8 items-center rounded-md px-2 text-[14px] text-muted hover:bg-fill3 hover:text-strong md:flex">
          Profile
        </Link>
        <ThemeToggle />
        <SolvedCounter />
      </div>
    </header>
  );
}

export function PanelTabs<T extends string>({ tabs, value, onChange, right }: { tabs: { key: T; label: string; icon: ReactNode }[]; value: T; onChange: (t: T) => void; right?: ReactNode }) {
  return (
    <div className="flex h-9 shrink-0 items-center gap-0.5 bg-header px-1.5">
      {tabs.map((t, i) => (
        <div key={t.key} className="flex items-center">
          {i > 0 && <span className="mx-0.5 h-4 w-px bg-divider" />}
          <button
            type="button"
            data-testid={`tab-${t.key}`}
            onClick={() => onChange(t.key)}
            className={`flex h-7 items-center gap-1.5 rounded-md px-2 text-[13px] ${value === t.key ? "font-medium text-strong" : "text-muted hover:bg-fill3 hover:text-label"}`}
          >
            {t.icon}
            {t.label}
          </button>
        </div>
      ))}
      <div className="ml-auto flex items-center">{right}</div>
    </div>
  );
}

export function Gutter() {
  return (
    <PanelResizeHandle className="gutter">
      <div className="grip" />
    </PanelResizeHandle>
  );
}

