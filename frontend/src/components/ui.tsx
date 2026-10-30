import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";
import type { Difficulty, Profile } from "../api/types";

export function cx(...c: (string | false | null | undefined)[]) {
  return c.filter(Boolean).join(" ");
}

type Variant = "primary" | "secondary" | "ghost" | "warm";
export function Button({
  variant = "primary", loading, className, children, ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; loading?: boolean }) {
  const styles: Record<Variant, string> = {
    primary: "bg-sage-600 text-white hover:bg-sage-700 shadow-soft",
    warm: "bg-clay-500 text-white hover:bg-clay-600 shadow-soft",
    secondary: "bg-card text-ink border border-line hover:border-sage-300 hover:bg-sage-50",
    ghost: "text-ink-soft hover:bg-black/5",
  };
  return (
    <button
      {...rest}
      disabled={rest.disabled || loading}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition",
        "disabled:opacity-50 disabled:cursor-not-allowed active:scale-[.98]",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-sage-300",
        styles[variant], className,
      )}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cx("rounded-2xl border border-line bg-card shadow-soft", className)}>{children}</div>;
}

const DIFF: Record<Difficulty, string> = {
  Beginner: "bg-sage-50 text-sage-700 border-sage-100",
  Intermediate: "bg-dusk-50 text-dusk-600 border-dusk-100",
  Advanced: "bg-honey-50 text-honey-600 border-honey-100",
  Expert: "bg-clay-50 text-clay-600 border-clay-100",
  Master: "bg-ink text-paper border-ink",
};
export function DifficultyBadge({ d }: { d: Difficulty }) {
  return <span className={cx("rounded-full border px-2.5 py-0.5 text-xs font-medium", DIFF[d])}>{d}</span>;
}

const AVATAR_BG = ["#DCE7DC", "#F5DCCF", "#F5E5B8", "#DADFEE", "#E8DDF0", "#D6E8EC"];
const AVATAR_FG = ["#3B5A41", "#A9583A", "#8A6516", "#525D90", "#6B4C85", "#2F6773"];
export function Avatar({ name, size = 48 }: { name: string; size?: number }) {
  let h = 0;
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  const i = h % AVATAR_BG.length;
  const initials = name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
  return (
    <div
      className="flex shrink-0 items-center justify-center rounded-full font-display font-semibold"
      style={{ width: size, height: size, background: AVATAR_BG[i], color: AVATAR_FG[i], fontSize: size * 0.38 }}
      aria-hidden
    >
      {initials}
    </div>
  );
}

export function ProgressBar({ value, max, className, tone = "sage" }: {
  value: number; max: number; className?: string; tone?: "sage" | "honey" | "clay";
}) {
  const pct = max > 0 ? Math.min(100, Math.max(0, (value / max) * 100)) : 0;
  const bar = { sage: "bg-sage-500", honey: "bg-honey-500", clay: "bg-clay-500" }[tone];
  return (
    <div className={cx("h-2 w-full overflow-hidden rounded-full bg-line/70", className)}>
      <div className={cx("h-full rounded-full transition-all duration-700", bar)} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function LevelBar({ profile }: { profile: Profile }) {
  const into = profile.xp - profile.xp_for_current_level;
  const need = profile.xp_for_next_level - profile.xp_for_current_level;
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between text-sm">
        <span className="font-medium">Level {profile.level} · <span className="text-ink-soft">{profile.difficulty}</span></span>
        <span className="tabular-nums text-ink-faint">{into} / {need} XP</span>
      </div>
      <ProgressBar value={into} max={need} tone="honey" />
    </div>
  );
}

export function ScoreRing({ value, label, size = 120, tone = "#5F8A66", big }: {
  value: number; label: string; size?: number; tone?: string; big?: boolean;
}) {
  const r = (size - 12) / 2;
  const c = 2 * Math.PI * r;
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#E6DFD3" strokeWidth={big ? 10 : 8} />
          <circle
            cx={size / 2} cy={size / 2} r={r} fill="none" stroke={tone} strokeWidth={big ? 10 : 8} strokeLinecap="round"
            strokeDasharray={c} strokeDashoffset={c * (1 - Math.min(100, value) / 100)}
            style={{ transition: "stroke-dashoffset 1.2s ease-out" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={cx("font-display font-semibold tabular-nums", big ? "text-4xl" : "text-2xl")}>{Math.round(value)}</span>
          <span className="text-[11px] text-ink-faint">/ 100</span>
        </div>
      </div>
      <span className="text-center text-sm font-medium text-ink-soft">{label}</span>
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-ink-soft">
      <Loader2 className="h-6 w-6 animate-spin text-sage-500" />
      {label && <p className="text-sm">{label}</p>}
    </div>
  );
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-xl border border-clay-100 bg-clay-50 px-4 py-3 text-sm text-clay-600">
      {message}
      {onRetry && <button onClick={onRetry} className="ml-2 font-medium underline">Try again</button>}
    </div>
  );
}

export function DemoBadge({ mode }: { mode?: string }) {
  if (mode !== "mock") return null;
  return (
    <span title="No GROK_API_KEY configured on the backend — using the simple offline demo engine."
      className="rounded-full border border-honey-100 bg-honey-50 px-2.5 py-0.5 text-xs font-medium text-honey-600">
      Offline demo AI
    </span>
  );
}
