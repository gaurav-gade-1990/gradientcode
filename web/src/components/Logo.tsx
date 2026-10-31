import { Link } from "react-router";

/** An original mark: a loss curve with a point rolling down to the minimum. */
export function LogoMark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <defs>
        <linearGradient id="gc-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#ffa116" />
          <stop offset="1" stopColor="#ff6a3d" />
        </linearGradient>
      </defs>
      <path d="M4 6c3.5 0 5 17 12 17s7.5-10 12-10" fill="none" stroke="url(#gc-grad)" strokeWidth="3.2" strokeLinecap="round" />
      <circle cx="16" cy="23" r="3.4" fill="#2cbb5d" />
    </svg>
  );
}

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <Link to="/" className="flex items-center gap-2 select-none" aria-label="GradientCode home">
      <LogoMark />
      {!compact && <span className="text-[16px] font-semibold tracking-tight text-strong">GradientCode</span>}
    </Link>
  );
}
