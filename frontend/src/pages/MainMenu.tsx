import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { BarChart3, DoorOpen, Leaf, Play } from "lucide-react";
import { usePlayer } from "../hooks/usePlayer";
import { Button, Card, ErrorNote, LevelBar, Spinner } from "../components/ui";

export default function MainMenu() {
  const { profile, loading, login, error } = usePlayer();
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const nav = useNavigate();

  if (loading) return <Spinner label="Opening the clinic…" />;

  const start = async () => {
    if (!name.trim()) return;
    setBusy(true); setErr(null);
    try { await login(name.trim()); nav("/clinic"); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-paper px-4">
      {/* soft decorative shapes */}
      <div className="pointer-events-none absolute -left-24 -top-24 h-80 w-80 rounded-full bg-sage-100/70 blur-2xl" />
      <div className="pointer-events-none absolute -bottom-32 -right-20 h-96 w-96 rounded-full bg-clay-100/60 blur-2xl" />

      <div className="relative w-full max-w-md animate-rise">
        <div className="mb-8 text-center">
          <span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-sage-500 text-white shadow-lift">
            <Leaf className="h-7 w-7" />
          </span>
          <h1 className="font-display text-4xl font-semibold tracking-tight">Therapist Simulator</h1>
          <p className="mt-2 text-ink-soft">Welcome to the Quiet Room Clinic. Listen closely — every patient has a story.</p>
        </div>

        <Card className="p-6">
          {error && <div className="mb-4"><ErrorNote message={error} /></div>}
          {profile ? (
            <div className="flex flex-col gap-5">
              <div>
                <p className="text-sm text-ink-soft">Welcome back,</p>
                <p className="font-display text-2xl font-semibold">{profile.display_name}</p>
              </div>
              <LevelBar profile={profile} />
              <div className="grid grid-cols-3 gap-2 text-center">
                <Stat label="XP" value={profile.xp} />
                <Stat label="Sessions" value={profile.sessions_completed} />
                <Stat label="Tier" value={profile.difficulty} />
              </div>
              <Button onClick={() => nav("/clinic")} className="py-3 text-base"><Play className="h-4 w-4" /> Play</Button>
              <Button variant="secondary" onClick={() => nav("/progress")}><BarChart3 className="h-4 w-4" /> Progress</Button>
            </div>
          ) : (
            <form onSubmit={(e) => { e.preventDefault(); start(); }} className="flex flex-col gap-4">
              <label className="text-sm font-medium" htmlFor="name">What should patients call you?</label>
              <input
                id="name" autoFocus value={name} maxLength={40} onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Dr. Kadam"
                className="rounded-xl border border-line bg-paper/60 px-4 py-3 focus:border-sage-300 focus:outline-none"
              />
              {err && <ErrorNote message={err} />}
              <Button type="submit" loading={busy} disabled={!name.trim()} className="py-3 text-base">
                <DoorOpen className="h-4 w-4" /> Open the clinic
              </Button>
              <p className="text-center text-xs text-ink-faint">A game about listening. Patients are fictional; this isn't therapy training or advice.</p>
            </form>
          )}
        </Card>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl bg-paper px-2 py-2.5">
      <div className="font-display text-lg font-semibold tabular-nums">{value}</div>
      <div className="text-[11px] uppercase tracking-wider text-ink-faint">{label}</div>
    </div>
  );
}
