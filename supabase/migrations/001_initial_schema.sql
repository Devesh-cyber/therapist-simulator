-- Therapist Simulator — initial schema for Supabase PostgreSQL
-- Run in Supabase: SQL Editor -> paste -> Run (or `supabase db push`).
--
-- Security model:
--   * The FastAPI backend connects with the database connection string (postgres role),
--     which bypasses RLS. It is the only component that reads hidden patient profiles.
--   * RLS is ENABLED on every table with NO policies for anon/authenticated roles,
--     so the public anon key (if ever exposed) cannot read or write anything —
--     in particular patients.hidden_profile is never reachable from a browser.

create extension if not exists "pgcrypto";

-- ---------- profiles ----------
create table if not exists public.profiles (
  id                  uuid primary key default gen_random_uuid(),
  display_name        varchar(60) not null,
  xp                  integer not null default 0 check (xp >= 0),
  level               integer not null default 1 check (level >= 1),
  sessions_completed  integer not null default 0 check (sessions_completed >= 0),
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

-- ---------- patients ----------
create table if not exists public.patients (
  id                  uuid primary key default gen_random_uuid(),
  owner_id            uuid not null references public.profiles(id) on delete cascade,
  name                varchar(80) not null,
  age                 integer not null check (age between 16 and 90),
  occupation          varchar(120) not null,
  level               integer not null default 1,
  difficulty          varchar(20) not null
                      check (difficulty in ('Beginner','Intermediate','Advanced','Expert','Master')),
  presenting_concern  text not null,
  reported_symptoms   jsonb not null default '[]'::jsonb,
  session_objective   text not null,
  hidden_profile      jsonb not null,           -- PRIVATE: backend only
  status              varchar(20) not null default 'waiting' check (status in ('waiting','seen')),
  created_at          timestamptz not null default now()
);
create index if not exists ix_patients_owner_status on public.patients(owner_id, status, created_at desc);

-- ---------- sessions ----------
create table if not exists public.sessions (
  id                uuid primary key default gen_random_uuid(),
  owner_id          uuid not null references public.profiles(id) on delete cascade,
  patient_id        uuid not null references public.patients(id) on delete cascade,
  status            varchar(20) not null default 'active'
                    check (status in ('active','ended','assessed','evaluated')),
  started_at        timestamptz not null default now(),
  ends_at           timestamptz not null,
  ended_at          timestamptz,
  end_reason        varchar(20) check (end_reason in ('manual','timeout','assessment')),
  notes             text not null default '',
  comfort           integer not null default 40 check (comfort between 0 and 100),
  context_summary   text not null default '',
  summarized_count  integer not null default 0,
  assessment        jsonb,
  created_at        timestamptz not null default now(),
  constraint uq_session_patient unique (patient_id),
  constraint ck_session_window check (ends_at > started_at)
);
create index if not exists ix_sessions_owner on public.sessions(owner_id, started_at desc);
create index if not exists ix_sessions_patient on public.sessions(patient_id);

-- ---------- messages ----------
create table if not exists public.messages (
  id          uuid primary key default gen_random_uuid(),
  session_id  uuid not null references public.sessions(id) on delete cascade,
  role        varchar(10) not null check (role in ('player','patient','system')),
  content     text not null,
  emotion     varchar(20),
  seq         integer not null,
  created_at  timestamptz not null default now(),
  constraint uq_message_seq unique (session_id, seq)
);
create index if not exists ix_messages_session on public.messages(session_id, seq);

-- ---------- patient_discoveries ----------
create table if not exists public.patient_discoveries (
  id                 uuid primary key default gen_random_uuid(),
  session_id         uuid not null references public.sessions(id) on delete cascade,
  fact_key           varchar(60) not null,
  category           varchar(60) not null,
  label              varchar(120) not null,
  detail             text not null,
  importance         integer not null default 1 check (importance between 1 and 3),
  state              varchar(20) not null default 'discovered'
                     check (state in ('discovered','important','connected')),
  evidence           text not null default '',
  source_message_id  uuid references public.messages(id) on delete set null,
  created_at         timestamptz not null default now(),
  constraint uq_discovery_session_fact unique (session_id, fact_key)   -- duplicate prevention
);
create index if not exists ix_discoveries_session on public.patient_discoveries(session_id);

-- ---------- evaluations ----------
create table if not exists public.evaluations (
  id                       uuid primary key default gen_random_uuid(),
  session_id               uuid not null unique references public.sessions(id) on delete cascade,
  overall_score            double precision not null check (overall_score between 0 and 100),
  satisfaction_score       double precision not null check (satisfaction_score between 0 and 100),
  understanding_score      double precision not null check (understanding_score between 0 and 100),
  category_scores          jsonb not null,
  satisfaction_breakdown   jsonb not null,
  understanding_breakdown  jsonb not null,
  feedback                 jsonb not null,
  xp_awarded               integer not null check (xp_awarded >= 0),
  created_at               timestamptz not null default now()
);

-- ---------- achievements ----------
create table if not exists public.achievements (
  code         varchar(40) primary key,
  title        varchar(80) not null,
  description  text not null,
  icon         varchar(40) not null default 'award'
);

create table if not exists public.user_achievements (
  id                uuid primary key default gen_random_uuid(),
  profile_id        uuid not null references public.profiles(id) on delete cascade,
  achievement_code  varchar(40) not null references public.achievements(code),
  session_id        uuid references public.sessions(id) on delete set null,
  earned_at         timestamptz not null default now(),
  constraint uq_user_achievement unique (profile_id, achievement_code)
);
create index if not exists ix_user_achievements_profile on public.user_achievements(profile_id);

insert into public.achievements (code, title, description, icon) values
  ('first_consult', 'First Consultation', 'Complete your first evaluated consultation.', 'stethoscope'),
  ('warm_presence', 'Warm Presence', 'Score 90+ in Empathy and Rapport.', 'heart'),
  ('detective',     'Full Picture', 'Discover every hidden fact about a patient.', 'search'),
  ('high_marks',    'High Marks', 'Reach an overall performance of 90+.', 'trophy'),
  ('regular',       'Clinic Regular', 'Complete 5 consultations.', 'calendar')
on conflict (code) do nothing;

-- ---------- updated_at trigger ----------
create or replace function public.touch_updated_at() returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end $$;
drop trigger if exists trg_profiles_updated on public.profiles;
create trigger trg_profiles_updated before update on public.profiles
  for each row execute function public.touch_updated_at();

-- ---------- Row Level Security ----------
alter table public.profiles            enable row level security;
alter table public.patients            enable row level security;
alter table public.sessions            enable row level security;
alter table public.messages            enable row level security;
alter table public.patient_discoveries enable row level security;
alter table public.evaluations         enable row level security;
alter table public.achievements        enable row level security;
alter table public.user_achievements   enable row level security;

-- Achievements catalogue is public, read-only.
grant select on public.achievements to anon, authenticated;
drop policy if exists "achievements are readable" on public.achievements;
create policy "achievements are readable" on public.achievements for select to anon, authenticated using (true);

-- Defence in depth: even if a future policy opens patients, the hidden profile column stays private.
revoke all on public.patients from anon, authenticated;
revoke all on public.profiles, public.sessions, public.messages, public.patient_discoveries,
              public.evaluations, public.user_achievements from anon, authenticated;
