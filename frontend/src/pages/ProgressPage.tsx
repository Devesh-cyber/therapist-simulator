import { useEffect, useState } from "react";
import { Award, Calendar, Heart, Lock, Search, Stethoscope, Trophy } from "lucide-react";
import { api } from "../api/client";
import type { Progress } from "../api/types";
import { Card, cx, ErrorNote, LevelBar, Spinner } from "../components/ui";

const ICONS: Record<string, typeof Award> = { stethoscope: Stethoscope, heart: Heart, search: Search, trophy: Trophy, calendar: Calendar };
const TIERS = [["1–3", "Beginner"], ["4–6", "Intermediate"], ["7–9", "Advanced"], ["10–15", "Expert"], ["16+", "Master"]];

export default function ProgressPage() {
  const [d, setD] = useState<Progress | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { api.progress().then(setD).catch((e) => setErr(e.message)); }, []);
  if (!d) return err ? <div className="mx-auto max-w-xl p-6"><ErrorNote message={err} /></div> : <Spinner />;

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="mb-6 font-display text-3xl font-semibold">Your progress</h1>
      <Card className="mb-5 p-6">
        <LevelBar profile={d.profile} />
        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[["Total XP", d.profile.xp], ["Sessions", d.profile.sessions_completed], ["Average", d.average_score ?? "–"], ["Best", d.best_score != null ? Math.round(d.best_score) : "–"]].map(([l, v]) => (
            <div key={l} className="rounded-xl bg-paper p-3 text-center">
              <div className="font-display text-2xl font-semibold tabular-nums">{v}</div>
              <div className="text-[11px] uppercase tracking-wider text-ink-faint">{l}</div>
            </div>
          ))}
        </div>
      </Card>

      <Card className="mb-5 p-6">
        <h2 className="mb-4 font-display text-lg font-semibold">Difficulty path</h2>
        <div className="grid grid-cols-5 gap-2">
          {TIERS.map(([lv, name]) => {
            const on = d.profile.difficulty === name;
            return (
              <div key={name} className={cx("rounded-xl border p-3 text-center", on ? "border-sage-300 bg-sage-50" : "border-line")}>
                <div className={cx("text-xs font-semibold sm:text-sm", on && "text-sage-700")}>{name}</div>
                <div className="text-[11px] text-ink-faint">Lv {lv}</div>
              </div>
            );
          })}
        </div>
        <p className="mt-3 text-xs text-ink-faint">Higher tiers bring more interconnected stories and more guarded patients — not more severe symptoms.</p>
      </Card>

      <Card className="p-6">
        <h2 className="mb-4 font-display text-lg font-semibold">Achievements</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {d.achievements.map((a) => {
            const Icon = a.earned ? ICONS[a.icon] ?? Award : Lock;
            return (
              <div key={a.code} className={cx("flex items-center gap-3 rounded-xl border p-3", a.earned ? "border-honey-100 bg-honey-50" : "border-line opacity-60")}>
                <span className={cx("flex h-10 w-10 items-center justify-center rounded-full", a.earned ? "bg-honey-100 text-honey-600" : "bg-line text-ink-faint")}><Icon className="h-5 w-5" /></span>
                <div><p className="text-sm font-semibold">{a.title}</p><p className="text-xs text-ink-soft">{a.description}</p></div>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
