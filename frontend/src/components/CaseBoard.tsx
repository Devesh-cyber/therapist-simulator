import { useEffect, useRef, useState } from "react";
import { Check, Link2, Lock, NotebookPen, Sparkles, Star } from "lucide-react";
import type { Board, BoardItem, PatientPublic } from "../api/types";
import { cx, ProgressBar } from "./ui";

const STATE_STYLE: Record<string, { box: string; icon: typeof Check; tag: string; tagText: string }> = {
  discovered: { box: "border-sage-100 bg-sage-50/60", icon: Check, tag: "bg-sage-100 text-sage-700", tagText: "Discovered" },
  important: { box: "border-honey-100 bg-honey-50", icon: Star, tag: "bg-honey-100 text-honey-600", tagText: "Important" },
  connected: { box: "border-dusk-100 bg-dusk-50", icon: Link2, tag: "bg-dusk-100 text-dusk-600", tagText: "Connected" },
};

function Item({ item, fresh, labelFor }: { item: BoardItem; fresh: boolean; labelFor: (k: string) => string }) {
  const s = STATE_STYLE[item.state] ?? STATE_STYLE.discovered;
  const Icon = s.icon;
  return (
    <div className={cx("rounded-xl border px-3 py-2.5", s.box, fresh && "animate-pop animate-glow")}>
      <div className="flex items-start gap-2">
        <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 opacity-70" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-sm font-medium leading-snug">{item.label}</span>
            <span className={cx("rounded-full px-1.5 py-px text-[10px] font-semibold uppercase tracking-wide", s.tag)}>{s.tagText}</span>
          </div>
          <p className="mt-0.5 text-xs leading-relaxed text-ink-soft">{item.detail}</p>
          {item.connected_to.length > 0 && (
            <p className="mt-1 text-[11px] text-dusk-600">↔ {item.connected_to.map(labelFor).join(", ")}</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function CaseBoard({
  board, patient, freshKeys, onSaveNotes, readOnly,
}: {
  board: Board;
  patient: PatientPublic;
  freshKeys: Set<string>;
  onSaveNotes?: (notes: string) => Promise<void>;
  readOnly?: boolean;
}) {
  const [notes, setNotes] = useState(board.notes);
  const [saved, setSaved] = useState<"idle" | "saving" | "saved">("idle");
  const timer = useRef<number>();
  useEffect(() => setNotes(board.notes), [board.session_id]); // eslint-disable-line react-hooks/exhaustive-deps

  const onNotes = (v: string) => {
    setNotes(v);
    if (!onSaveNotes) return;
    window.clearTimeout(timer.current);
    setSaved("saving");
    timer.current = window.setTimeout(async () => {
      try { await onSaveNotes(v); setSaved("saved"); } catch { setSaved("idle"); }
    }, 800);
  };

  const byKey = Object.fromEntries(board.items.map((i) => [i.key, i.label]));
  const labelFor = (k: string) => byKey[k] ?? "…";

  return (
    <div className="flex flex-col gap-4">
      <div>
        <div className="mb-2 flex items-baseline justify-between">
          <h2 className="font-display text-lg font-semibold">Patient Case Board</h2>
          <span className="text-sm tabular-nums text-ink-soft">
            <span className="font-semibold text-ink">{board.discovered_count}</span> / {board.total_facts} discoveries
          </span>
        </div>
        <ProgressBar value={board.discovered_count} max={board.total_facts} />
      </div>

      {/* Always-known sections */}
      <section>
        <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-ink-faint">Basic Information</h3>
        <p className="text-sm">{patient.name}, {patient.age} · {patient.occupation}</p>
      </section>
      <section>
        <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-ink-faint">Presenting Concern</h3>
        <div className="flex flex-wrap gap-1.5">
          {patient.reported_symptoms.map((s) => (
            <span key={s} className="rounded-full border border-line bg-paper px-2.5 py-0.5 text-xs">{s}</span>
          ))}
        </div>
      </section>

      {board.categories.map((c) => {
        const items = board.items.filter((i) => i.category === c.name);
        const unknown = c.total - items.length;
        const done = unknown === 0;
        return (
          <section key={c.name}>
            <div className="mb-1.5 flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-faint">{c.name}</h3>
              <span className={cx("text-xs tabular-nums", done ? "font-semibold text-sage-600" : "text-ink-faint")}>
                {done && <Sparkles className="mr-1 inline h-3 w-3" />}{items.length}/{c.total}
              </span>
            </div>
            <div className="flex flex-col gap-1.5">
              {items.map((i) => <Item key={i.key} item={i} fresh={freshKeys.has(i.key)} labelFor={labelFor} />)}
              {Array.from({ length: unknown }).map((_, n) => (
                <div key={n} className="flex items-center gap-2 rounded-xl border border-dashed border-line px-3 py-2 text-xs text-ink-faint">
                  <Lock className="h-3 w-3" /> Unknown — keep exploring
                </div>
              ))}
            </div>
          </section>
        );
      })}

      <section>
        <div className="mb-1.5 flex items-center justify-between">
          <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-ink-faint">
            <NotebookPen className="h-3.5 w-3.5" /> My notes
          </h3>
          <span className="text-[11px] text-ink-faint">{saved === "saving" ? "Saving…" : saved === "saved" ? "Saved" : ""}</span>
        </div>
        <textarea
          value={notes}
          readOnly={readOnly}
          onChange={(e) => onNotes(e.target.value)}
          rows={4}
          placeholder="Hunches, connections, things to ask about…"
          className="w-full resize-y rounded-xl border border-line bg-paper/60 px-3 py-2 text-sm placeholder:text-ink-faint focus:border-sage-300 focus:outline-none"
        />
      </section>
    </div>
  );
}
