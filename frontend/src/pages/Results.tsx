import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowRight, Award, Eye, Sparkles, ThumbsUp, TrendingUp } from "lucide-react";
import { api, ApiError } from "../api/client";
import type { Results as R } from "../api/types";
import { usePlayer } from "../hooks/usePlayer";
import { Avatar, Button, Card, ErrorNote, LevelBar, ProgressBar, ScoreRing, Spinner } from "../components/ui";

const CAT_LABELS: Record<string, [string, string]> = {
  empathy_rapport: ["Empathy and Rapport", "20%"],
  question_relevance: ["Question Relevance", "20%"],
  active_listening: ["Active Listening", "15%"],
  understanding_symptoms: ["Understanding Symptoms", "20%"],
  underlying_concerns: ["Identifying Underlying Concerns", "15%"],
  next_steps: ["Appropriate Next Steps", "10%"],
};
const nice = (k: string) => k.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

export default function Results() {
  const { id } = useParams();
  const nav = useNavigate();
  const { setProfile } = usePlayer();
  const [r, setR] = useState<R | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [nexting, setNexting] = useState(false);

  const load = useCallback(async () => {
    setErr(null);
    try {
      let res: R;
      try { res = await api.results(id!); }
      catch (e) {
        if (e instanceof ApiError && e.status === 404) res = await api.evaluate(id!);
        else throw e;
      }
      setR(res); setProfile(res.profile);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) nav(`/session/${id}/assessment`, { replace: true });
      else setErr((e as Error).message);
    }
  }, [id, nav, setProfile]);
  useEffect(() => { load(); }, [load]);

  const next = async () => {
    setNexting(true);
    try { const p = await api.generatePatient(); nav(`/patient/${p.id}`); }
    catch (e) { setErr((e as Error).message); setNexting(false); }
  };

  if (!r) return err ? <div className="mx-auto max-w-xl p-6"><ErrorNote message={err} onRetry={load} /></div>
    : <Spinner label="Your supervisor is reviewing the session…" />;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex items-center gap-3 animate-rise">
        <Avatar name={r.patient.name} size={48} />
        <div>
          <p className="text-sm text-ink-soft">Consultation results · {r.patient.name}</p>
          <h1 className="font-display text-3xl font-semibold">{r.rating}</h1>
        </div>
      </div>

      <Card className="mb-5 p-6 animate-pop">
        <div className="grid items-center gap-6 sm:grid-cols-3">
          <ScoreRing value={r.overall_score} label="Overall performance" size={150} big />
          <ScoreRing value={r.satisfaction_score} label="Patient satisfaction" tone="#C9714A" />
          <ScoreRing value={r.understanding_score} label="Patient understanding" tone="#6672A8" />
        </div>
      </Card>

      <div className="mb-5 grid gap-5 md:grid-cols-2">
        <Card className="p-6">
          <h2 className="mb-4 flex items-center gap-2 font-display text-lg font-semibold"><TrendingUp className="h-5 w-5 text-sage-500" /> Performance breakdown</h2>
          <div className="flex flex-col gap-3">
            {Object.entries(CAT_LABELS).map(([k, [label, w]]) => (
              <div key={k}>
                <div className="mb-1 flex justify-between text-sm">
                  <span>{label} <span className="text-xs text-ink-faint">· {w}</span></span>
                  <span className="font-semibold tabular-nums">{Math.round(r.category_scores[k] ?? 0)}</span>
                </div>
                <ProgressBar value={r.category_scores[k] ?? 0} max={100} />
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-6">
          <h2 className="mb-4 flex items-center gap-2 font-display text-lg font-semibold"><ThumbsUp className="h-5 w-5 text-clay-500" /> Feedback</h2>
          {r.feedback.summary && <p className="mb-4 text-sm text-ink-soft">{r.feedback.summary}</p>}
          <ul className="mb-4 flex flex-col gap-2">
            {r.feedback.strengths.map((t) => <li key={t} className="flex gap-2 text-sm"><span className="text-sage-500">●</span>{t}</li>)}
          </ul>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-faint">To work on</h3>
          <ul className="flex flex-col gap-2">
            {r.feedback.improvements.map((t) => <li key={t} className="flex gap-2 text-sm"><span className="text-clay-400">●</span>{t}</li>)}
          </ul>
        </Card>
      </div>

      <div className="mb-5 grid gap-5 md:grid-cols-3">
        <Card className="p-6">
          <h2 className="mb-3 flex items-center gap-2 font-display text-lg font-semibold"><Eye className="h-5 w-5 text-dusk-500" /> Discovery</h2>
          <p className="font-display text-3xl font-semibold tabular-nums">{r.discovered_count}<span className="text-lg text-ink-faint"> / {r.total_facts}</span></p>
          <p className="mb-3 text-sm text-ink-soft">facts uncovered</p>
          {r.missed_categories.length > 0 && (
            <p className="text-xs text-ink-soft">Unexplored areas: <span className="font-medium text-ink">{r.missed_categories.join(", ")}</span></p>
          )}
        </Card>
        <Card className="p-6">
          <h2 className="mb-3 font-display text-lg font-semibold">How {r.patient.name.split(" ")[0]} felt</h2>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
            {Object.entries(r.satisfaction_breakdown).map(([k, v]) => (
              <div key={k} className="flex justify-between"><span className="text-ink-soft">{nice(k)}</span><span className="tabular-nums">{Math.round(v)}</span></div>
            ))}
          </div>
        </Card>
        <Card className="p-6">
          <h2 className="mb-3 font-display text-lg font-semibold">Understanding</h2>
          <div className="flex flex-col gap-1.5 text-sm">
            {Object.entries(r.understanding_breakdown).map(([k, v]) => (
              <div key={k} className="flex justify-between"><span className="text-ink-soft">{nice(k)}</span><span className="tabular-nums">{Math.round(v)}</span></div>
            ))}
          </div>
        </Card>
      </div>

      <Card className="flex flex-col gap-4 p-6 sm:flex-row sm:items-center">
        <div className="flex items-center gap-3">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-honey-50 text-honey-600"><Sparkles className="h-6 w-6" /></span>
          <div>
            <p className="font-display text-2xl font-semibold text-honey-600">+{r.xp_awarded} XP</p>
            {r.leveled_up && <p className="text-sm font-medium text-sage-700">Level up! You're now level {r.profile.level}.</p>}
          </div>
        </div>
        <div className="flex-1 sm:px-6"><LevelBar profile={r.profile} /></div>
        <Button onClick={next} loading={nexting} className="py-3">Next patient <ArrowRight className="h-4 w-4" /></Button>
      </Card>

      {r.new_achievements.length > 0 && (
        <div className="mt-5 flex flex-wrap gap-3">
          {r.new_achievements.map((a) => (
            <div key={a.code} className="flex animate-pop items-center gap-3 rounded-2xl border border-honey-100 bg-honey-50 px-4 py-3">
              <Award className="h-5 w-5 text-honey-600" />
              <div><p className="text-sm font-semibold">{a.title}</p><p className="text-xs text-ink-soft">{a.description}</p></div>
            </div>
          ))}
        </div>
      )}
      <div className="mt-6 text-center">
        <Button variant="ghost" onClick={() => nav("/clinic")}>Back to clinic</Button>
      </div>
    </div>
  );
}
