import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { PatientPublic } from "../api/types";
import { useScene } from "../game/useScene";
import "../game/game.css";

/** Intake form on a clipboard, over the empty consultation room. */
export default function Arrival() {
  const { id } = useParams();
  const [p, setP] = useState<PatientPublic | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const { hostRef } = useScene();
  const nav = useNavigate();

  useEffect(() => { api.getPatient(id!).then(setP).catch((e) => setErr(e.message)); }, [id]);

  const start = async () => {
    setStarting(true); setErr(null);
    try { const s = await api.startSession(id!); nav(`/session/${s.id}`); }
    catch (e) { setErr((e as Error).message); setStarting(false); }
  };

  const first = p?.name.split(" ")[0];
  return (
    <div className="game">
      <div className="scenehost" ref={hostRef} />
      <div className="dim" />
      <div className="overlay">
        <div className="sheet clipboard">
          {!p ? (
            <p>{err ?? "Fetching the intake form…"}</p>
          ) : (
            <>
              <div className="label" style={{ textAlign: "center" }}>New patient · intake form</div>
              <div className="field"><span className="k">Name</span><span className="hand">{p.name}</span></div>
              <div className="field"><span className="k">Age</span><span className="hand">{p.age}</span></div>
              <div className="field"><span className="k">Occupation</span><span className="hand">{p.occupation}</span></div>
              <div className="field"><span className="k">Level</span><span className="hand">{p.level} · {p.difficulty}</span></div>
              <div className="field"><span className="k">Reports</span><span className="hand">{p.reported_symptoms.join(", ")}</span></div>
              <div className="field" style={{ marginTop: 4 }}><span className="k">Goal</span><span style={{ lineHeight: "32px", fontSize: 15 }}>{p.session_objective}</span></div>
              {err && <div className="err">{err}</div>}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, marginTop: 20, flexWrap: "wrap" }}>
                <button className="btn quiet" onClick={() => nav("/clinic")}>Back to clinic</button>
                <button className="btn" onClick={start} disabled={starting}>
                  {starting ? "Opening the door…" : p.status === "seen" ? `Continue with ${first}` : `Invite ${first} in`}
                </button>
              </div>
              <p style={{ fontSize: 13, color: "var(--soft)", margin: "12px 0 0" }}>10 minutes · the clock starts when they sit down</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
