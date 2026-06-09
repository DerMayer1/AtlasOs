-- ============================================================
-- AtlasOS — Initial Schema
-- Migration: 001_initial_schema
-- ============================================================

-- Enable UUID generation
create extension if not exists "pgcrypto";

-- ── users ────────────────────────────────────────────────
create table if not exists public.users (
  id          uuid        primary key default gen_random_uuid(),
  email       text        not null unique,
  name        text,
  tier        text        not null default 'free' check (tier in ('free', 'pro')),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- ── analyses ─────────────────────────────────────────────
create table if not exists public.analyses (
  id            uuid        primary key default gen_random_uuid(),
  user_id       uuid        not null references public.users(id) on delete cascade,
  status        text        not null default 'pending' check (status in ('pending', 'running', 'complete', 'failed')),
  depth         text        not null default 'standard' check (depth in ('quick', 'standard', 'deep')),
  input         jsonb       not null,
  result        jsonb,
  error         text,
  duration_ms   integer,
  created_at    timestamptz not null default now(),
  completed_at  timestamptz
);

create index if not exists analyses_user_id_idx on public.analyses(user_id);
create index if not exists analyses_status_idx  on public.analyses(status);

-- ── competitors ──────────────────────────────────────────
create table if not exists public.competitors (
  id           uuid        primary key default gen_random_uuid(),
  analysis_id  uuid        not null references public.analyses(id) on delete cascade,
  name         text        not null,
  website      text,
  type         text        not null check (type in ('direct', 'indirect', 'substitute', 'adjacent', 'future')),
  threat_level text        check (threat_level in ('low', 'medium', 'high')),
  summary      text,
  positioning  text,
  metadata     jsonb,
  created_at   timestamptz not null default now()
);

create index if not exists competitors_analysis_id_idx on public.competitors(analysis_id);

-- ── memos ────────────────────────────────────────────────
create table if not exists public.memos (
  id            uuid        primary key default gen_random_uuid(),
  analysis_id   uuid        not null unique references public.analyses(id) on delete cascade,
  content_md    text        not null,
  content_html  text,
  exported_at   timestamptz,
  export_count  integer     not null default 0,
  created_at    timestamptz not null default now()
);

-- ── exports ──────────────────────────────────────────────
create table if not exists public.exports (
  id            uuid        primary key default gen_random_uuid(),
  memo_id       uuid        not null references public.memos(id) on delete cascade,
  user_id       uuid        not null references public.users(id),
  format        text        not null check (format in ('pdf', 'markdown', 'docx')),
  storage_path  text,
  created_at    timestamptz not null default now()
);

create index if not exists exports_user_id_idx on public.exports(user_id);
create index if not exists exports_memo_id_idx on public.exports(memo_id);

-- ── Row Level Security ───────────────────────────────────
alter table public.users      enable row level security;
alter table public.analyses   enable row level security;
alter table public.competitors enable row level security;
alter table public.memos      enable row level security;
alter table public.exports    enable row level security;

-- Users can only read/update their own profile
drop policy if exists "users: own row" on public.users;
create policy "users: own row" on public.users
  for all using ((select auth.uid()) = id);

-- Analyses scoped to owner
drop policy if exists "analyses: own rows" on public.analyses;
create policy "analyses: own rows" on public.analyses
  for all using ((select auth.uid()) = user_id);

-- Competitors visible only through owned analyses
drop policy if exists "competitors: own analyses" on public.competitors;
create policy "competitors: own analyses" on public.competitors
  for all using (
    exists (
      select 1 from public.analyses a
      where a.id = analysis_id and a.user_id = (select auth.uid())
    )
  );

-- Memos visible only through owned analyses
drop policy if exists "memos: own analyses" on public.memos;
create policy "memos: own analyses" on public.memos
  for all using (
    exists (
      select 1 from public.analyses a
      where a.id = analysis_id and a.user_id = (select auth.uid())
    )
  );

-- Exports scoped to owner
drop policy if exists "exports: own rows" on public.exports;
create policy "exports: own rows" on public.exports
  for all using ((select auth.uid()) = user_id);

-- ── updated_at trigger ───────────────────────────────────
create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists users_updated_at on public.users;
create trigger users_updated_at
  before update on public.users
  for each row execute function public.set_updated_at();
