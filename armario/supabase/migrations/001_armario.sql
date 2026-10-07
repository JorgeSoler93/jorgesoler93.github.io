-- Armario: tablas para Supabase/Postgres (también válido en Postgres a secas).
create table if not exists armario_items (
  id          text primary key,
  name        text not null,
  category    text not null check (category in ('top','bottom','dress','shoes','outerwear','accessory')),
  subcategory text not null default '',
  colors      text[] not null default '{}',
  pattern     text not null default 'liso',
  material    text not null default '',
  formality   int  not null default 2 check (formality between 1 and 5),
  warmth      int  not null default 2 check (warmth between 1 and 5),
  seasons     text[] not null default '{}',
  style_tags  text[] not null default '{}',
  notes       text not null default '',
  image_file  text not null default '',
  clean_file  text not null default '',
  source_url  text not null default '',
  status      text not null default 'clean' check (status in ('clean','dirty')),
  wear_count  int  not null default 0,
  last_worn   timestamptz,
  created_at  timestamptz not null default now()
);

create table if not exists armario_outfits (
  id          text primary key,
  item_ids    text[] not null,
  occasion    text not null default '',
  explanation text not null default '',
  score       double precision not null default 0,
  rating      int check (rating between 1 and 5),
  worn_on     timestamptz,
  created_at  timestamptz not null default now()
);

create index if not exists armario_items_category_idx on armario_items (category);
create index if not exists armario_outfits_created_idx on armario_outfits (created_at desc);

-- Solo se accede con la service key desde el backend; nada público.
alter table armario_items   enable row level security;
alter table armario_outfits enable row level security;
