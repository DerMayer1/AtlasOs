create table if not exists public.workspaces (
  id                  uuid        primary key default gen_random_uuid(),
  user_id             uuid        not null references public.users(id) on delete cascade,
  name                text        not null,
  company_name        text        not null,
  website_url         text        not null,
  description         text        not null,
  target_market       text,
  category_label      text,
  category_definition text,
  status              text        not null default 'draft'
                                  check (status in ('draft', 'discovering', 'review', 'active', 'failed')),
  error               text,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

create index if not exists workspaces_user_id_idx
  on public.workspaces(user_id);

create table if not exists public.tracked_companies (
  id            uuid        primary key default gen_random_uuid(),
  workspace_id  uuid        not null references public.workspaces(id) on delete cascade,
  name          text        not null,
  website_url   text,
  type          text        not null
                            check (type in ('subject', 'direct', 'indirect', 'substitute', 'adjacent', 'future')),
  threat_level  text        check (threat_level in ('low', 'medium', 'high')),
  summary       text,
  positioning   text,
  is_subject    boolean     not null default false,
  is_confirmed  boolean     not null default false,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (workspace_id, name)
);

create index if not exists tracked_companies_workspace_id_idx
  on public.tracked_companies(workspace_id);

alter table public.workspaces enable row level security;
alter table public.tracked_companies enable row level security;

drop policy if exists "workspaces: own rows" on public.workspaces;
create policy "workspaces: own rows" on public.workspaces
  for all using ((select auth.uid()) = user_id);

drop policy if exists "tracked companies: own workspace" on public.tracked_companies;
create policy "tracked companies: own workspace" on public.tracked_companies
  for all using (
    exists (
      select 1 from public.workspaces w
      where w.id = workspace_id and w.user_id = (select auth.uid())
    )
  );

drop trigger if exists workspaces_updated_at on public.workspaces;
create trigger workspaces_updated_at
  before update on public.workspaces
  for each row execute function public.set_updated_at();

drop trigger if exists tracked_companies_updated_at on public.tracked_companies;
create trigger tracked_companies_updated_at
  before update on public.tracked_companies
  for each row execute function public.set_updated_at();
