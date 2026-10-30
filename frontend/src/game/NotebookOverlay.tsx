import { useRef, useState } from "react";
import type { Board, PatientPublic } from "../api/types";

/** The case board, drawn as a handwritten notebook page. */
export default function NotebookOverlay({
  board, patient, fresh, onClose, onSaveNotes, closeLabel = "Back to the conversation", readOnly,
}: {
  board: Board; patient: PatientPublic; fresh: Set<string>; onClose: () => void;
  onSaveNotes?: (n: string) => Promise<void>; closeLabel?: string; readOnly?: boolean;
}) {
  const [notes, setNotes] = useState(board.notes);
  const t = useRef<number>();
  const byKey = Object.fromEntries(board.items.map((i) => [i.key, i.label]));

  const onNotes = (v: string) => {
    setNotes(v);
    if (!onSaveNotes) return;
    window.clearTimeout(t.current);
    t.current = window.setTimeout(() => { onSaveNotes(v).catch(() => undefined); }, 700);
  };

  return (
    <div className="overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="sheet book">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
          <h2 style={{ fontSize: 24 }}>{patient.name} · case notes</h2>
          <span style={{ color: "var(--soft)", fontVariantNumeric: "tabular-nums" }}>{board.discovered_count} of {board.total_facts} discovered</span>
        </div>
        <div className="hand" style={{ margin: "6px 0 4px" }}>
          {patient.age}, {patient.occupation} — reports {patient.reported_symptoms.join(", ").toLowerCase()}
        </div>
        <div className="bookgrid" style={{ marginTop: 8 }}>
          {board.categories.map((c) => {
            const items = board.items.filter((i) => i.category === c.name);
            return (
              <div className="cat" key={c.name}>
                <h3><span>{c.name}</span><span>{items.length}/{c.total}</span></h3>
                {items.map((i) => (
                  <div key={i.key} className={`ins ${i.state} ${fresh.has(i.key) ? "fresh" : ""}`}>
                    {i.label}<small>{i.state}</small>
                    <span style={{ display: "block", fontSize: 19, lineHeight: "24px", color: "#4A5B7F" }}>{i.detail}</span>
                    {i.connected_to.length > 0 && <span className="lk">↔ {i.connected_to.map((k) => byKey[k]).join(", ")}</span>}
                  </div>
                ))}
                {Array.from({ length: c.total - items.length }).map((_, n) => <div key={n} className="unknown">· · · still unknown</div>)}
              </div>
            );
          })}
        </div>
        <h3 style={{ fontFamily: "var(--body)", fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: ".08em", color: "var(--soft)", lineHeight: "32px", marginTop: 6 }}>
          <label htmlFor="notesTa">My notes</label>
        </h3>
        <textarea id="notesTa" className="notes" value={notes} readOnly={readOnly} onChange={(e) => onNotes(e.target.value)} placeholder="Hunches, connections, things to ask…" />
        <div style={{ textAlign: "right", marginTop: 10 }}><button className="btn" onClick={onClose}>{closeLabel}</button></div>
      </div>
    </div>
  );
}
