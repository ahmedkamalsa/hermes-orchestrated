
-- جدول ذاكرة الأخطاء للتعلم التراكمي
create table if not exists mistakes (
  id uuid primary key default gen_random_uuid(),
  type text not null, -- web_search_failed / model_limit / mcp_error / vision_404
  query text not null,
  source text, -- URL أو model name
  error text,
  created_at timestamptz default now()
);
create table if not exists learnings (
  id uuid primary key default gen_random_uuid(),
  pattern text not null, -- نمط الخطأ
  solution text not null, -- الحل
  hits int default 1,
  created_at timestamptz default now()
);
-- RLS: allow anon read/write (free tier)
alter table mistakes enable row level security;
alter table learnings enable row level security;
drop policy if exists "allow all" on mistakes;
drop policy if exists "allow all" on learnings;
create policy "allow all" on mistakes for all using (true) with check (true);
create policy "allow all" on learnings for all using (true) with check (true);
