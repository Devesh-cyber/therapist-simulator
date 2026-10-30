import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { HistoryItem } from "../api/types";
import { Avatar, Card, DifficultyBadge, ErrorNote, Spinner } from "../components/ui";

const target = (h: HistoryItem) =>
  h.status === "active" ? `/session/${h.session_id}`
    : h.status === "ended" ? `/session/${h.session_id}/assessment`
      : `/session/${h.session_id}/results`;

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { api.history().then(setItems).catch((e) => setErr(e.message)); }, []);
  if (!items) return err ? <div className="mx-auto max-w-xl p-6"><ErrorNote message={err} /></div> : <Spinner />;

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="mb-6 font-display text-3xl font-semibold">Session history</h1>
      {items.length === 0 ? (
        <Card className="p-8 text-center text-ink-soft">No consultations yet. Your first patient is waiting in the clinic.</Card>
      ) : (
        <Card className="divide-y divide-line">
          {items.map((h) => (
            <Link key={h.session_id} to={target(h)} className="flex items-center gap-3 px-5 py-3.5 transition hover:bg-paper">
              <Avatar name={h.patient_name} size={40} />
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{h.patient_name}</p>
                <p className="truncate text-xs text-ink-faint">{h.patient_occupation} · {new Date(h.started_at).toLocaleString()}</p>
              </div>
              <span className="hidden sm:block"><DifficultyBadge d={h.difficulty} /></span>
              <div className="w-20 text-right">
                {h.overall_score != null ? (
                  <>
                    <p className="font-display text-lg font-semibold tabular-nums">{Math.round(h.overall_score)}</p>
                    <p className="text-[11px] text-honey-600">+{h.xp_awarded} XP</p>
                  </>
                ) : <span className="text-xs capitalize text-ink-faint">{h.status}</span>}
              </div>
            </Link>
          ))}
        </Card>
      )}
    </div>
  );
}
