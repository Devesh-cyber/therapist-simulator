import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { PlayerProvider, usePlayer } from "./hooks/usePlayer";
import Layout from "./components/Layout";
import { Spinner } from "./components/ui";
import MainMenu from "./pages/MainMenu";
import Clinic from "./pages/Clinic";
import Arrival from "./pages/Arrival";
import Consultation from "./pages/Consultation";
import Assessment from "./pages/Assessment";
import Results from "./pages/Results";
import ProgressPage from "./pages/ProgressPage";
import HistoryPage from "./pages/HistoryPage";
import SettingsPage from "./pages/SettingsPage";

function Protected({ children }: { children: ReactNode }) {
  const { profile, loading } = usePlayer();
  if (loading) return <Spinner />;
  return profile ? <>{children}</> : <Navigate to="/" replace />;
}

export default function App() {
  return (
    <PlayerProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainMenu />} />
          {/* full-screen game rooms (no app chrome) */}
          <Route path="/patient/:id" element={<Protected><Arrival /></Protected>} />
          <Route path="/session/:id" element={<Protected><Consultation /></Protected>} />
          <Route element={<Protected><Layout /></Protected>}>
            <Route path="/clinic" element={<Clinic />} />
            <Route path="/session/:id/assessment" element={<Assessment />} />
            <Route path="/session/:id/results" element={<Results />} />
            <Route path="/progress" element={<ProgressPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </PlayerProvider>
  );
}
