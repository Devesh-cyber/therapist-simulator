import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { LogOut, Save } from "lucide-react";
import { api } from "../api/client";
import { usePlayer } from "../hooks/usePlayer";
import { Button, Card, ErrorNote } from "../components/ui";

export default function SettingsPage() {
  const { profile, setProfile, logout } = usePlayer();
  const [name, setName] = useState(profile?.display_name ?? "");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [health, setHealth] = useState<string>("checking…");
  const nav = useNavigate();

  useEffect(() => {
    const base = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
    fetch(`${base}/api/health`).then((r) => r.json())
      .then((h) => setHealth(h.llm_mode === "grok" ? `Connected · Grok (${h.model})` : "Connected · offline demo AI (no Grok key)"))
      .catch(() => setHealth("Backend unreachable"));
  }, []);

  const save = async () => {
    setErr(null); setMsg(null);
    try { setProfile(await api.rename(name.trim())); setMsg("Saved"); } catch (e) { setErr((e as Error).message); }
  };

  return (
    <div className="mx-auto max-w-xl px-4 py-8">
      <h1 className="mb-6 font-display text-3xl font-semibold">Settings</h1>
      <Card className="mb-5 flex flex-col gap-3 p-6">
        <label className="text-sm font-medium" htmlFor="dn">Display name</label>
        <div className="flex gap-2">
          <input id="dn" value={name} maxLength={40} onChange={(e) => setName(e.target.value)}
            className="flex-1 rounded-xl border border-line bg-paper/60 px-3 py-2 focus:border-sage-300 focus:outline-none" />
          <Button onClick={save} disabled={!name.trim()}><Save className="h-4 w-4" /> Save</Button>
        </div>
        {msg && <p className="text-sm text-sage-600">{msg}</p>}
        {err && <ErrorNote message={err} />}
      </Card>
      <Card className="mb-5 p-6">
        <p className="text-sm font-medium">Server</p>
        <p className="text-sm text-ink-soft">{health}</p>
      </Card>
      <Card className="p-6">
        <p className="mb-1 text-sm font-medium">Sign out</p>
        <p className="mb-3 text-sm text-ink-soft">This is a guest profile stored on this device. Signing out loses access to it.</p>
        <Button variant="warm" onClick={() => { logout(); nav("/"); }}><LogOut className="h-4 w-4" /> Sign out</Button>
      </Card>
    </div>
  );
}
