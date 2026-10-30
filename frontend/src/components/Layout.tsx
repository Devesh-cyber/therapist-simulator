import { NavLink, Outlet, Link } from "react-router-dom";
import { BarChart3, History, Home, Leaf, Settings } from "lucide-react";
import { usePlayer } from "../hooks/usePlayer";
import { cx } from "./ui";

const NAV = [
  { to: "/clinic", label: "Clinic", icon: Home },
  { to: "/progress", label: "Progress", icon: BarChart3 },
  { to: "/history", label: "History", icon: History },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function Layout() {
  const { profile } = usePlayer();
  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="sticky top-0 z-30 border-b border-line/70 bg-paper/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4">
          <Link to="/" className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-sage-500 text-white"><Leaf className="h-4 w-4" /></span>
            <span className="hidden font-display text-lg font-semibold sm:inline">Quiet Room Clinic</span>
          </Link>
          <nav className="ml-auto flex items-center gap-1">
            {NAV.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} className={({ isActive }) => cx(
                "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm transition",
                isActive ? "bg-sage-50 text-sage-700 font-medium" : "text-ink-soft hover:bg-black/5",
              )}>
                <Icon className="h-4 w-4" /><span className="hidden md:inline">{label}</span>
              </NavLink>
            ))}
          </nav>
          {profile && (
            <div className="hidden items-center gap-2 rounded-full border border-line bg-card px-3 py-1 text-sm sm:flex">
              <span className="font-medium">{profile.display_name}</span>
              <span className="rounded-full bg-honey-50 px-2 text-xs font-semibold text-honey-600">Lv {profile.level}</span>
            </div>
          )}
        </div>
      </header>
      <main><Outlet /></main>
    </div>
  );
}
