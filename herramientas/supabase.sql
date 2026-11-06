-- ¿Con quién te quedas? · Ranking de la afición (Supabase / Postgres)
-- Cada orden terminado se guarda de forma anónima: equipo + lista de nombres en el orden elegido.
-- Los visitantes solo pueden AÑADIR órdenes y leer las estadísticas agregadas; nunca leer, cambiar ni borrar filas.

create table if not exists public.rankings (
  id bigint generated always as identity primary key,
  team_id text not null check (team_id ~ '^[0-9]{1,8}$'),
  players text[] not null check (array_length(players, 1) between 2 and 60),
  created_at timestamptz not null default now()
);
create index if not exists rankings_team_idx on public.rankings (team_id);

alter table public.rankings enable row level security;
drop policy if exists "anon puede añadir" on public.rankings;
create policy "anon puede añadir" on public.rankings for insert to anon with check (true);
revoke select, update, delete on public.rankings from anon, authenticated;
grant insert on public.rankings to anon;

-- Estadísticas por jugador de un equipo (n.º 1, top 3, 3 últimos, cuarto superior/inferior y posición media relativa)
create or replace function public.community_stats(p_team text)
returns json language sql stable security definer set search_path = public as $$
  with r as (
    select id, players, array_length(players, 1) as n from rankings where team_id = p_team
  ), e as (
    select r.n, u.name, u.pos from r, unnest(r.players) with ordinality as u(name, pos)
  ), s as (
    select name,
           count(*)                                        as c,
           count(*) filter (where pos = 1)                 as first,
           count(*) filter (where pos <= 3)                as top3,
           count(*) filter (where pos > n - 3)             as bottom3,
           count(*) filter (where pos <= ceil(n / 4.0))    as topq,
           count(*) filter (where pos > n - ceil(n / 4.0)) as botq,
           avg((pos - 1)::float / greatest(n - 1, 1))      as avgpos
    from e group by name
  )
  select json_build_object('total', (select count(*) from r),
                           'players', coalesce((select json_agg(s) from s), '[]'::json));
$$;
revoke all on function public.community_stats(text) from public;
grant execute on function public.community_stats(text) to anon;
