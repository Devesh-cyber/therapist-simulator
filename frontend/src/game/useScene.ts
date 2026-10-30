import { useEffect, useRef, useState } from "react";
import { createScene, type Scene } from "./scene.js";

/** Mounts the illustrated room into a div and returns the scene controller. */
export function useScene() {
  const hostRef = useRef<HTMLDivElement>(null);
  const [scene, setScene] = useState<Scene | null>(null);
  useEffect(() => {
    if (hostRef.current) setScene(createScene(hostRef.current));
  }, []);
  return { hostRef, scene };
}

/** Typewriter for the dialogue box. Calls onDone when the full line is visible. */
export function useTypewriter() {
  const [text, setText] = useState("");
  const [typing, setTyping] = useState(false);
  const timer = useRef<number>();
  const full = useRef("");
  const done = useRef<(() => void) | undefined>();

  const finish = () => {
    window.clearInterval(timer.current);
    setText(full.current);
    setTyping(false);
    const cb = done.current; done.current = undefined; cb?.();
  };
  const type = (line: string, onDone?: () => void) => {
    window.clearInterval(timer.current);
    full.current = line; done.current = onDone;
    let i = 0;
    setText(""); setTyping(true);
    timer.current = window.setInterval(() => {
      i += 2;
      if (i >= line.length) finish(); else setText(line.slice(0, i));
    }, 30);
  };
  const show = (line: string) => { window.clearInterval(timer.current); full.current = line; setText(line); setTyping(false); };
  useEffect(() => () => window.clearInterval(timer.current), []);
  return { text, typing, type, show, skip: () => typing && finish() };
}
