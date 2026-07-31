create table if not exists public.friendship_results (
    owner_id text primary key,
    result jsonb not null,
    updated_at timestamptz not null default now()
);

alter table public.friendship_results enable row level security;

revoke all on table public.friendship_results from anon, authenticated;

comment on table public.friendship_results is
    'Private friendship-map results. Accessed only by the Streamlit server.';
