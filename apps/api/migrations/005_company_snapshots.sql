alter table public.tracked_companies
  add column if not exists monitoring_status text not null default 'idle'
    check (monitoring_status in ('idle', 'pending', 'running', 'ready', 'failed')),
  add column if not exists last_snapshot_at timestamptz,
  add column if not exists snapshot_error text;

create table if not exists public.company_snapshots (
  id             uuid        primary key default gen_random_uuid(),
  workspace_id   uuid        not null references public.workspaces(id) on delete cascade,
  company_id     uuid        not null references public.tracked_companies(id) on delete cascade,
  website_url    text        not null,
  final_url      text,
  page_title     text,
  page_description text,
  content_hash   text        not null,
  content_text   text        not null,
  metadata       jsonb       not null default '{}'::jsonb,
  captured_at    timestamptz not null default now()
);

create index if not exists company_snapshots_workspace_id_idx
  on public.company_snapshots(workspace_id, captured_at desc);

create index if not exists company_snapshots_company_id_idx
  on public.company_snapshots(company_id, captured_at desc);

alter table public.company_snapshots enable row level security;

drop policy if exists "company snapshots: own workspace" on public.company_snapshots;
create policy "company snapshots: own workspace" on public.company_snapshots
  for all using (
    exists (
      select 1 from public.workspaces w
      where w.id = workspace_id and w.user_id = (select auth.uid())
    )
  );

grant select, insert, update, delete on public.company_snapshots to service_role;
grant select, insert, update, delete on public.tracked_companies to service_role;
