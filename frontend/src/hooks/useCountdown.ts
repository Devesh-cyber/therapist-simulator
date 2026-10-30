import { useEffect, useRef, useState } from "react";

/** Countdown driven by the SERVER's end time. The client clock offset is corrected using
 *  server_now, so a wrong local clock doesn't change the timer. The server still enforces it. */
export function useCountdown(endsAt: string | null, serverNow: string | null, active: boolean) {
  const offset = useRef(0);
  const [left, setLeft] = useState(0);

  useEffect(() => {
    if (serverNow) offset.current = new Date(serverNow).getTime() - Date.now();
  }, [serverNow]);

  useEffect(() => {
    if (!endsAt || !active) { setLeft(0); return; }
    const end = new Date(endsAt).getTime();
    const tick = () => setLeft(Math.max(0, Math.round((end - (Date.now() + offset.current)) / 1000)));
    tick();
    const id = setInterval(tick, 500);
    return () => clearInterval(id);
  }, [endsAt, active]);

  return left;
}

export const fmtClock = (s: number) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
