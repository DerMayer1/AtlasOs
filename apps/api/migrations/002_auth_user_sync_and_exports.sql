-- Keep the application profile table aligned with Supabase Auth.
create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.users (id, email, name)
  values (
    new.id,
    coalesce(new.email, ''),
    coalesce(new.raw_user_meta_data ->> 'name', new.raw_user_meta_data ->> 'full_name')
  )
  on conflict (id) do update
    set email = excluded.email,
        name = coalesce(excluded.name, public.users.name);

  return new;
end;
$$;

revoke all on function public.handle_new_auth_user() from public;
revoke all on function public.handle_new_auth_user() from anon;
revoke all on function public.handle_new_auth_user() from authenticated;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert or update of email, raw_user_meta_data on auth.users
  for each row execute function public.handle_new_auth_user();

-- Backfill users created before this trigger existed.
insert into public.users (id, email, name)
select
  id,
  coalesce(email, ''),
  coalesce(raw_user_meta_data ->> 'name', raw_user_meta_data ->> 'full_name')
from auth.users
on conflict (id) do update
  set email = excluded.email,
      name = coalesce(excluded.name, public.users.name);

create or replace function public.increment_export_count(memo_id uuid)
returns void
language sql
security definer
set search_path = public
as $$
  update public.memos
  set export_count = export_count + 1,
      exported_at = now()
  where id = memo_id;
$$;

revoke all on function public.increment_export_count(uuid) from public;
revoke all on function public.increment_export_count(uuid) from anon;
revoke all on function public.increment_export_count(uuid) from authenticated;
grant execute on function public.increment_export_count(uuid) to service_role;
