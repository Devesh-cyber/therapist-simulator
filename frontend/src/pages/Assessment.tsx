import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ClipboardCheck } from "lucide-react";
import { api } from "../api/client";
import type { Assessment as A, Session } from "../api/types";
import CaseBoard from "../components/CaseBoard";
import { Avatar, Button, Card, ErrorNote, Spinner } from "../components/ui";

const FIELDS: { key: keyof A; label: string; hint: string; required?: boolean }[] = [
  { key: "main_concern", label: "Main concern", hint: "What do you believe is really going on for them?", required: true },
  { key: "important_symptoms", label: "Important symptoms & experiences", hint: "What are they experiencing day to day?" },
  { key: "underlying_concerns", label: "Underlying concerns", hint: "What deeper worries or patterns sit beneath the surface? How do they connect?" },
  { key: "important_discoveries", label: "Key discoveries", hint: "Which facts mattered most? Anything you're still unsure about?" },
  { key: "next_steps", label: "Suggested next steps", hint: "How would you approach the next sessions?", required: true },
];

export default function Assessment() {
  const { id } = useParams();
  const nav = useNavigate();
  const [s, setS] = useState<Session | null>(null);
  const [form, setForm] = useState<A>({ main_concern: "", important_symptoms: "", underlying_concerns: "", important_discoveries: "", next_steps: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.getSession(id!).then((d) => {
      if (d.status === "evaluated" || d.status === "assessed") nav(`/session/${id}/results`, { replace: true });
      setS(d);
    }).catch((e) => setErr(e.message));
  }, [id, nav]);

  const valid = form.main_concern.trim().length >= 3 && form.next_steps.trim().length >= 3;

  const submit = async () => {
    setBusy(true); setErr(null);
    try { await api.submitAssessment(id!, form); nav(`/session/${id}/results`); }
    catch (e) { setErr((e as Error).message); setBusy(false); }
  };

  if (!s) return err ? <div className="mx-auto max-w-xl p-6"><ErrorNote message={err} /></div> : <Spinner />;

  return (
    <div className="mx-auto grid max-w-6xl gap-6 px-4 py-8 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div>
        <div className="mb-6 flex items-center gap-3">
          <Avatar name={s.patient.name} size={48} />
          <div>
            <p className="text-sm text-ink-soft">Final assessment</p>
            <h1 className="font-display text-2xl font-semibold">What did you understand about {s.patient.name.split(" ")[0]}?</h1>
          </div>
        </div>
        {s.status === "active" && (
          <p className="mb-4 rounded-xl bg-honey-50 px-4 py-2 text-sm text-honey-600">Submitting will end the consultation.</p>
        )}
        <Card className="flex flex-col gap-5 p-6">
          {FIELDS.map((f) => (
            <label key={f.key} className="flex flex-col gap-1.5">
              <span className="text-sm font-medium">{f.label}{f.required && <span className="text-clay-500"> *</span>}</span>
              <span className="text-xs text-ink-faint">{f.hint}</span>
              <textarea
                rows={3} maxLength={1500} value={form[f.key]}
                onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                className="resize-y rounded-xl border border-line bg-paper/60 px-3 py-2 text-sm focus:border-sage-300 focus:outline-none"
              />
            </label>
          ))}
          {err && <ErrorNote message={err} />}
          <Button onClick={submit} disabled={!valid} loading={busy} className="self-end px-6 py-3">
            <ClipboardCheck className="h-4 w-4" /> Submit & get feedback
          </Button>
        </Card>
      </div>
      <Card className="h-fit p-5 lg:sticky lg:top-20">
        <CaseBoard board={s.board} patient={s.patient} freshKeys={new Set()} readOnly />
      </Card>
    </div>
  );
}
