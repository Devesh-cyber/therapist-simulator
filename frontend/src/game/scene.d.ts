export type Emotion = "neutral" | "warm" | "sad" | "anxious" | "guarded" | "tearful" | "relieved" | "frustrated" | "thinking";
export interface Look {
  gender: string; hair: string; hairColor: string; skin: number; outfit: string; glasses: boolean; beard: boolean; age: number;
}
export interface Scene {
  setPatient(look: Look | null): void;
  setEmotion(e: string): void;
  getEmotion(): Emotion;
  setTalking(on: boolean): void;
  setThinking(on: boolean): void;
  setTime(progress: number, secondsLeft: number): void;
  enter(): Promise<void>;
  leave(): Promise<void>;
  show(): void;
}
export const EMOTIONS: Emotion[];
export function normalizeLook(look: Record<string, unknown> | null | undefined, name?: string, age?: number): Look;
export function createScene(host: HTMLElement): Scene;
