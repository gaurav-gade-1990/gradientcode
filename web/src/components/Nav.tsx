import type { ReactNode } from "react";
import { NavLink, useLocation } from "react-router";
import { useIndex, useProgress, useTheme } from "../lib/hooks";
import { setTheme } from "../lib/storage";
import { IconCheck, IconMoon, IconSun } from "./Icons";
import { Logo } from "./Logo";

export function ThemeToggle() {
  const theme = useTheme();
  return (
    <button
      type="button"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      className="flex h-8 w-8 items-center justify-center rounded-md text-muted hover:bg-fill3 hover:text-strong"
      title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
      aria-label="Toggle theme"
      data-testid="theme-toggle"
    >
      {theme === "dark" ? <IconSun size={17} /> : <IconMoon size={17} />}
    </button>
  );
}

export function SolvedCounter() {
  const { solved } = useProgress();
  const { index } = useIndex();
  const built = new Set(index?.problems.map((p) => p.slug) ?? []);
  const n = Object.keys(solved).filter((s) => !index || built.has(s)).length;
  return (
    <div className="flex h-8 items-center gap-1.5 rounded-md bg-fill3 px-2.5 text-[13px] text-label" title="Problems solved" data-testid="solved-counter">
      <IconCheck size={14} className="text-gc-green" />
      <span className="font-medium text-strong">{n}</span>
      <span className="text-muted">/ {index?.problems.length ?? "–"}</span>
    </div>
  );
}

const linkCls = ({ isActive }: { isActive: boolean }) =>
  `relative flex h-full items-center px-1 text-[14px] transition-colors ${
    isActive ? "text-strong after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[2px] after:rounded-full after:bg-strong" : "text-muted hover:text-strong"
  }`;

export function NavLinks() {
  const { pathname } = useLocation();
  return (
    <nav className="flex h-full items-center gap-5">
      <NavLink to="/problemset" className={({ isActive }) => linkCls({ isActive: isActive || pathname === "/" })}>
        Problems
      </NavLink>
      <NavLink to="/study-plans" className={linkCls}>
        Study Plans
      </NavLink>
      <NavLink to="/profile" className={linkCls}>
        Profile
      </NavLink>
    </nav>
  );
}

/** The site nav on the list, study plan and profile pages. */
export function TopNav() {
  return (
    <header className="sticky top-0 z-30 h-[50px] border-b border-line bg-layer1">
      <div className="mx-auto flex h-full max-w-[1200px] items-center gap-6 px-6">
        <Logo />
        <NavLinks />
        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
          <SolvedCounter />
        </div>
      </div>
    </header>
  );
}

export function PageShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-full bg-page">
      <TopNav />
      <main className="mx-auto max-w-[1200px] px-6 py-6">{children}</main>
    </div>
  );
}
