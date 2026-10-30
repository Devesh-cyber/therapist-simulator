export type Difficulty = "Beginner" | "Intermediate" | "Advanced" | "Expert" | "Master";

export interface Profile {
  id: string;
  display_name: string;
  xp: number;
  level: number;
  difficulty: Difficulty;
  sessions_completed: number;
  xp_for_current_level: number;
  xp_for_next_level: number;
}

export interface PatientPublic {
  id: string;
  name: string;
  age: number;
  occupation: string;
  level: number;
  difficulty: Difficulty;
  presenting_concern: string;
  reported_symptoms: string[];
  session_objective: string;
  status: "waiting" | "seen";
  look: Record<string, unknown>;
  opening_emotion: string;
}

export type DiscoveryState = "discovered" | "important" | "connected";

export interface BoardItem {
  key: string;
  category: string;
  label: string;
  detail: string;
  importance: number;
  state: DiscoveryState;
  evidence: string;
  connected_to: string[];
}

export interface BoardCategory {
  name: string;
  total: number;
  discovered: number;
}

export interface Board {
  session_id: string;
  total_facts: number;
  discovered_count: number;
  categories: BoardCategory[];
  items: BoardItem[];
  notes: string;
}

export interface Message {
  id: string;
  role: "player" | "patient" | "system";
  content: string;
  emotion?: string | null;
  created_at: string;
}

export type SessionStatus = "active" | "ended" | "assessed" | "evaluated";

export interface Session {
  id: string;
  status: SessionStatus;
  started_at: string;
  ends_at: string;
  ended_at: string | null;
  server_now: string;
  seconds_remaining: number;
  patient: PatientPublic;
  messages: Message[];
  board: Board;
  has_assessment: boolean;
  comfort: number;
  llm_mode: "grok" | "mock";
}

export interface SendMessageResult {
  player_message: Message;
  patient_message: Message | null;
  new_discoveries: BoardItem[];
  updated_items: BoardItem[];
  discovered_count: number;
  total_facts: number;
  seconds_remaining: number;
  status: SessionStatus;
  comfort: number;
  error: string | null;
}

export interface Assessment {
  main_concern: string;
  important_symptoms: string;
  underlying_concerns: string;
  important_discoveries: string;
  next_steps: string;
}

export interface Achievement {
  code: string;
  title: string;
  description: string;
  icon: string;
  earned?: boolean;
  earned_at?: string | null;
}

export interface Results {
  session_id: string;
  patient: PatientPublic;
  overall_score: number;
  rating: string;
  satisfaction_score: number;
  understanding_score: number;
  category_scores: Record<string, number>;
  satisfaction_breakdown: Record<string, number>;
  understanding_breakdown: Record<string, number>;
  feedback: { strengths: string[]; improvements: string[]; summary: string };
  xp_awarded: number;
  discovered_count: number;
  total_facts: number;
  missed_categories: string[];
  profile: Profile;
  new_achievements: Achievement[];
  leveled_up: boolean;
}

export interface HistoryItem {
  session_id: string;
  patient_name: string;
  patient_occupation: string;
  difficulty: Difficulty;
  status: SessionStatus;
  started_at: string;
  overall_score: number | null;
  xp_awarded: number | null;
}

export interface Progress {
  profile: Profile;
  achievements: Achievement[];
  recent: HistoryItem[];
  average_score: number | null;
  best_score: number | null;
  waiting_patient: PatientPublic | null;
  open_session_id: string | null;
  open_session_status: SessionStatus | null;
  llm_mode: "grok" | "mock";
}
