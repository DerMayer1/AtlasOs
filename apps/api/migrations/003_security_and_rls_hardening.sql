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

revoke all on function public.handle_new_auth_user() from public;
revoke all on function public.handle_new_auth_user() from anon;
revoke all on function public.handle_new_auth_user() from authenticated;

drop policy if exists "users: own row" on public.users;
create policy "users: own row" on public.users
  for all using ((select auth.uid()) = id);

drop policy if exists "analyses: own rows" on public.analyses;
create policy "analyses: own rows" on public.analyses
  for all using ((select auth.uid()) = user_id);

drop policy if exists "competitors: own analyses" on public.competitors;
create policy "competitors: own analyses" on public.competitors
  for all using (
    exists (
      select 1 from public.analyses a
      where a.id = analysis_id and a.user_id = (select auth.uid())
    )
  );

drop policy if exists "memos: own analyses" on public.memos;
create policy "memos: own analyses" on public.memos
  for all using (
    exists (
      select 1 from public.analyses a
      where a.id = analysis_id and a.user_id = (select auth.uid())
    )
  );

drop policy if exists "exports: own rows" on public.exports;
create policy "exports: own rows" on public.exports
  for all using ((select auth.uid()) = user_id);

create index if not exists exports_memo_id_idx on public.exports(memo_id);
