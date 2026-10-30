import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Bell, Coffee, DoorOpen, Sofa, Trophy } from "lucide-react";
import { api } from "../api/client";
import type { Progress } from "../api/types";
import { usePlayer } from "../hooks/usePlayer";
import { Avatar, Button, Card, DemoBadge, DifficultyBadge, ErrorNote, LevelBar, Spinner } from "../components/ui";

export default function Clinic() {
  const { setProfile } = usePlayer();
  const [data, setData] = useState<Progress | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [calling, setCalling] = useState(false);
  const nav = useNavigate();

  const load = async () => {
    setErr(null);
    try { const p = await api.progress(); setData(p); setProfile(p.profile); } catch (e) { setErr((e as Error).message); }
  };
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const callNext = async () => {
    setCalling(true); setErr(null);
    try { const p = await api.generatePatient(); nav(`/patient/${p.id}`); }
    catch (e) { setErr((e as Error).message); setCalling(false); }
  };

  if (!data) return err ? <div className="mx-auto max-w-xl p-6"><ErrorNote message={err} onRetry={load} /></div> : <Spinner label="Tidying the waiting room…" />;

  const open = data.open_session_id;
  const openTarget = data.open_session_status === "active" ? `/session/${open}`
    : data.open_session_status === "assessed" ? `/session/${open}/results` : `/session/${open}/assessment`;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-ink-soft">Clinic Dashboard</p>
          <h1 className="font-display text-3xl font-semibold">Good to see you, {data.profile.display_name}.</h1>
        </div>
        <DemoBadge mode={data.llm_mode} />
      </div>

      <div className="grid gap-5 md:grid-cols-3">
        {/* Waiting room */}
        <Card className="relative overflow-hidden p-6 md:col-span-2">
          <div className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-sage-50" />
          <div className="relative">
            <div className="mb-4 flex items-center gap-2 text-sm font-medium text-sage-700">
              <Sofa className="h-4 w-4" /> Waiting room
            </div>
            {open ? (
              <div className="flex flex-col gap-4">
                <p className="text-ink-soft">You have an unfinished consultation.</p>
                <Button onClick={() => nav(openTarget)} className="self-start">Continue consultation <ArrowRight className="h-4 w-4" /></Button>
              </div>
            ) : data.waiting_patient ? (
              <div className="flex flex-col gap-4">
                <div className="flex items-center gap-4">
                  <Avatar name={data.waiting_patient.name} size={56} />
                  <div>
                    <p className="font-display text-xl font-semibold">{data.waiting_patient.name}</p>
                    <p className="text-sm text-ink-soft">{data.waiting_patient.age} · {data.waiting_patient.occupation}</p>
                  </div>
                  <span className="ml-auto"><DifficultyBadge d={data.waiting_patient.difficulty} /></span>
                </div>
                <p className="flex items-center gap-2 text-sm text-ink-soft"><Bell className="h-4 w-4 text-honey-500" /> Is waiting to be seen.</p>
                <Button onClick={() => nav(`/patient/${data.waiting_patient!.id}`)} className="self-start">
                  <DoorOpen className="h-4 w-4" /> Invite them in
                </Button>
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                <p className="flex items-center gap-2 text-ink-soft"><Coffee className="h-4 w-4" /> The waiting room is quiet. Ready for your next patient?</p>
                <Button onClick={callNext} loading={calling} className="self-start">
                  {calling ? "A patient is arriving…" : <>Call next patient <ArrowRight className="h-4 w-4" /></>}
                </Button>
              </div>
            )}
            {err && <div className="mt-4"><ErrorNote message={err} /></div>}
          </div>
        </Card>

        {/* Player card */}
        <Card className="flex flex-col gap-4 p-6">
          <LevelBar profile={data.profile} />
          <div className="grid grid-cols-2 gap-2 text-center">
            <div className="rounded-xl bg-paper p-3"><div className="font-display text-xl font-semibold">{data.profile.sessions_completed}</div><div className="text-[11px] uppercase tracking-wider text-ink-faint">Sessions</div></div>
            <div className="rounded-xl bg-paper p-3"><div className="font-display text-xl font-semibold">{data.average_score ?? "–"}</div><div className="text-[11px] uppercase tracking-wider text-ink-faint">Avg score</div></div>
          </div>
          <Link to="/progress" className="flex items-center gap-1.5 text-sm font-medium text-sage-600 hover:underline">
            <Trophy className="h-4 w-4" /> {data.achievements.filter((a) => a.earned).length}/{data.achievements.length} achievements
          </Link>
        </Card>
      </div>

      {data.recent.length > 0 && (
        <Card className="mt-5 p-6">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold">Recent consultations</h2>
            <Link to="/history" className="text-sm text-sage-600 hover:underline">All history</Link>
          </div>
          <ul className="divide-y divide-line">
            {data.recent.map((h) => (
              <li key={h.session_id} className="flex items-center gap-3 py-2.5">
                <Avatar name={h.patient_name} size={32} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{h.patient_name}</p>
                  <p className="truncate text-xs text-ink-faint">{h.patient_occupation}</p>
                </div>
                {h.overall_score != null
                  ? <Link to={`/session/${h.session_id}/results`} className="text-sm font-semibold tabular-nums text-sage-700">{Math.round(h.overall_score)}</Link>
                  : <span className="text-xs text-ink-faint">{h.status}</span>}
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
