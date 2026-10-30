import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { BoardItem, Session } from "../api/types";
import { fmtClock, useCountdown } from "../hooks/useCountdown";
import { normalizeLook } from "../game/scene.js";
import { useScene, useTypewriter } from "../game/useScene";
import NotebookOverlay from "../game/NotebookOverlay";
import "../game/game.css";

type Overlay = null | "notebook" | "log" | "confirm";

export default function Consultation() {
  const { id } = useParams();
  const nav = useNavigate();
  const { hostRef, scene } = useScene();
  const tw = useTypewriter();
  const [s, setS] = useState<Session | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [speaker, setSpeaker] = useState<"patient" | "you">("patient");
  const [canReply, setCanReply] = useState(false);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [overlay, setOverlay] = useState<Overlay>(null);
  const [fresh, setFresh] = useState<Set<string>>(new Set());
  const [unseen, setUnseen] = useState(0);
  const [bump, setBump] = useState(0);
  const [leaving, setLeaving] = useState(false);
  const started = useRef(false);
  const nbRef = useRef<HTMLButtonElement>(null);
  const sayRef = useRef<HTMLTextAreaElement>(null);

  const load = useCallback(async () => {
    try {
      const d = await api.getSession(id!);
      if (d.status === "evaluated" || d.status === "assessed") { nav(`/session/${id}/results`, { replace: true }); return null; }
      setS(d); return d;
    } catch (e) { setErr((e as Error).message); return null; }
  }, [id, nav]);
  useEffect(() => { load(); }, [load]);

  const active = s?.status === "active" && !leaving;
  const left = useCountdown(s?.ends_at ?? null, s?.server_now ?? null, s?.status === "active");
  const first = s?.patient.name.split(" ")[0] ?? "";

  const patientSays = useCallback((line: string, emotion?: string | null) => {
    if (!scene) return;
    setSpeaker("patient"); setCanReply(false);
    if (emotion) scene.setEmotion(emotion);
    scene.setTalking(true);
    tw.type(line, () => { scene.setTalking(false); setCanReply(true); setTimeout(() => sayRef.current?.focus(), 30); });
  }, [scene, tw]);

  // Arrival (fresh session) or resume.
  useEffect(() => {
    if (!s || !scene || started.current) return;
    started.current = true;
    scene.setPatient(normalizeLook(s.patient.look, s.patient.name, s.patient.age));
    const lastPatient = [...s.messages].reverse().find((m) => m.role === "patient");
    if (s.messages.length === 0) {
      scene.setEmotion(s.patient.opening_emotion);
      scene.enter().then(() => patientSays(s.patient.presenting_concern));
    } else {
      scene.show();
      if (lastPatient) { scene.setEmotion(lastPatient.emotion || "neutral"); tw.show(lastPatient.content); }
      setCanReply(true);
    }
    if (s.status !== "active") { setCanReply(false); farewellAndLeave("time"); }
  }, [s, scene]); // eslint-disable-line react-hooks/exhaustive-deps

  // Room clock + window light follow the server-anchored countdown.
  useEffect(() => {
    if (!scene || !s) return;
    const total = (new Date(s.ends_at).getTime() - new Date(s.started_at).getTime()) / 1000 || 600;
    const secs = s.status === "active" ? left : 0;
    scene.setTime((total - secs) / total, secs);
    if (s.status === "active" && left === 0 && started.current) {
      load().then((d) => { if (d && d.status !== "active") farewellAndLeave("time"); });
    }
  }, [left, scene, s?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const farewellAndLeave = async (reason: "time" | "manual") => {
    if (!scene || leaving) return;
    setLeaving(true); setCanReply(false); setOverlay(null); scene.setThinking(false);
    const bye = reason === "time" ? "Oh — is that the time already? Thank you for listening today." : "Okay. Thank you for today. It helped to talk.";
    patientSays(bye, (s?.comfort ?? 40) >= 50 ? "relieved" : "neutral");
    await new Promise((r) => setTimeout(r, 2600));
    tw.skip(); scene.setTalking(false);
    await scene.leave();
    nav(`/session/${id}/assessment`);
  };

  const flyNote = (label: string) => {
    const nb = nbRef.current?.getBoundingClientRect(); if (!nb) return;
    const n = document.createElement("div"); n.className = "flyer"; n.textContent = "✎ " + label; document.body.appendChild(n);
    const w = n.offsetWidth, sx = innerWidth / 2 - w / 2, sy = innerHeight * 0.32;
    const a = n.animate([
      { transform: `translate(${sx}px,${sy + 20}px) scale(.9)`, opacity: 0 },
      { transform: `translate(${sx}px,${sy}px) scale(1)`, opacity: 1, offset: 0.25 },
      { transform: `translate(${sx}px,${sy}px) scale(1)`, opacity: 1, offset: 0.6 },
      { transform: `translate(${nb.left + nb.width / 2 - w / 2}px,${nb.top + 20}px) scale(.3) rotate(-12deg)`, opacity: 0.2 },
    ], { duration: 2000, easing: "ease-in-out" });
    a.onfinish = () => { n.remove(); setBump((b) => b + 1); };
  };

  const send = async () => {
    const text = draft.trim();
    if (!text || !s || busy || !active || !scene) return;
    setBusy(true); setErr(null); setDraft(""); setCanReply(false);
    setSpeaker("you"); tw.show(text);
    scene.setThinking(true);
    try {
      const r = await api.sendMessage(s.id, text);
      scene.setThinking(false);
      setS((prev) => {
        if (!prev) return prev;
        const upd = new Map(r.updated_items.map((i) => [i.key, i]));
        return {
          ...prev, status: r.status, comfort: r.comfort,
          messages: [...prev.messages, r.player_message, ...(r.patient_message ? [r.patient_message] : [])],
          board: { ...prev.board, discovered_count: r.discovered_count, items: [...prev.board.items.map((i) => upd.get(i.key) ?? i), ...r.new_discoveries] },
        };
      });
      if (r.patient_message) patientSays(r.patient_message.content, r.patient_message.emotion);
      else { setErr(r.error ?? "The patient didn't answer. Try again."); setDraft(text); setCanReply(true); scene.setEmotion("neutral"); }
      if (r.new_discoveries.length) {
        setFresh(new Set([...r.new_discoveries, ...r.updated_items].map((i: BoardItem) => i.key)));
        setUnseen((u) => u + r.new_discoveries.length);
        r.new_discoveries.forEach((d, i) => setTimeout(() => flyNote(d.label), 600 + i * 700));
      }
      if (r.status !== "active") farewellAndLeave("time");
    } catch (e) {
      scene.setThinking(false); scene.setEmotion("neutral");
      setErr((e as Error).message); setDraft(text); setCanReply(true);
      load();
    } finally { setBusy(false); }
  };

  const endNow = async () => {
    if (!s) return;
    setOverlay(null);
    try { await api.endSession(s.id); farewellAndLeave("manual"); } catch (e) { setErr((e as Error).message); }
  };

  return (
    <div className="game">
      <div className="scenehost" ref={hostRef} />
      {!s && (
        <div className="overlay"><div className="sheet log">{err ?? "Preparing the room…"}</div></div>
      )}
      {s && (
        <>
          <div className="hud">
            <div className="who">
              <b>{s.patient.name}</b>
              <div className="comfort" title="How comfortable the patient feels with you">
                <span>Comfort</span>
                <span className="m"><i style={{ width: `${Math.max(6, s.comfort)}%`, backgroundPosition: `${100 - s.comfort}% 0` }} /></span>
              </div>
              {s.llm_mode === "mock" && <span style={{ fontSize: 11, color: "var(--honey)" }}>Offline demo AI</span>}
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", justifyContent: "flex-end" }}>
              <span className={`chip timer ${active && left <= 60 ? "low" : ""}`}>{s.status === "active" ? fmtClock(left) : "Ended"}</span>
              {active && <button className="chip" style={{ border: 0 }} onClick={() => setOverlay("confirm")}>End session</button>}
            </div>
          </div>

          <button
            ref={nbRef} key={bump} className={`notebook ${bump ? "bump" : ""}`} aria-label="Open case notebook"
            onClick={() => { setUnseen(0); setOverlay("notebook"); }}
          >
            <span className="t">Case notes</span>
            <span className="n">{s.board.discovered_count} / {s.board.total_facts}</span>
            {unseen > 0 && <span className="badge">+{unseen}</span>}
          </button>

          <div className="dialog">
            <div className="dbox">
              <div className={`nameplate ${speaker === "you" ? "you" : ""}`}>{speaker === "you" ? "You" : first}</div>
              <div className="line" aria-live="polite" onClick={tw.skip}>
                {tw.text}{tw.typing && <span className="caret">▍</span>}
              </div>
              {canReply && active && (
                <form className="reply" onSubmit={(e) => { e.preventDefault(); send(); }}>
                  <textarea
                    ref={sayRef} id="say" rows={1} maxLength={800} value={draft} aria-label="Your response"
                    placeholder="What do you say?" onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                  />
                  <button className="btn" disabled={!draft.trim() || busy}>Say</button>
                </form>
              )}
              <div className="dtools">
                <span>{tw.typing ? "Tap the text to skip" : s.messages.length === 0 && canReply ? "Tip: open questions and warmth help people open up." : ""}</span>
                <button className="linkbtn" type="button" onClick={() => setOverlay("log")}>Session log</button>
              </div>
              {err && <div className="err">{err}</div>}
            </div>
          </div>

          {overlay === "notebook" && (
            <NotebookOverlay
              board={s.board} patient={s.patient} fresh={fresh} readOnly={!active}
              onClose={() => { setOverlay(null); setFresh(new Set()); }}
              onSaveNotes={async (n) => { await api.saveNotes(s.id, n); }}
            />
          )}
          {overlay === "log" && (
            <div className="overlay" onClick={(e) => e.target === e.currentTarget && setOverlay(null)}>
              <div className="sheet log">
                <h2 style={{ fontSize: 22, marginBottom: 8 }}>Session log</h2>
                <div className="entry"><b style={{ color: "var(--clay)" }}>{first}</b><div>{s.patient.presenting_concern}</div></div>
                {s.messages.map((m) => (
                  <div className="entry" key={m.id}>
                    <b style={{ color: m.role === "player" ? "var(--sage)" : "var(--clay)" }}>{m.role === "player" ? "You" : first}</b>
                    <div>{m.content}</div>
                  </div>
                ))}
                <div style={{ textAlign: "right", marginTop: 14 }}><button className="btn" onClick={() => setOverlay(null)}>Close</button></div>
              </div>
            </div>
          )}
          {overlay === "confirm" && (
            <div className="overlay">
              <div className="sheet log">
                <h2 style={{ fontSize: 22 }}>End the session?</h2>
                <p style={{ color: "var(--soft)" }}>{first} will leave and you'll write up your notes.</p>
                <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                  <button className="btn quiet" onClick={() => setOverlay(null)}>Keep talking</button>
                  <button className="btn clay" onClick={endNow}>End session</button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
