-- AgriSense AI
-- 3 of 4. Run after 20261109000002_core_tables.sql.
--
-- Embedding column is extensions.vector(1536), cosine distance, HNSW index.
-- This matches common models such as text-embedding-3-small.
-- If EMBEDDING_MODEL uses another dimension, change this column before inserting chunks.
-- Page numbers and section labels belong in knowledge_chunks.metadata.
-- Do not insert a citation that was not produced from an ingested document.

-- ---------------------------------------------------------------------------
-- knowledge_documents
-- ---------------------------------------------------------------------------

create table public.knowledge_documents (
  id uuid primary key default extensions.gen_random_uuid(),
  title text not null,
  source_organization text not null,
  document_url text,
  crop text,
  disease text,
  region text,
  publication_date date,
  storage_path text,
  ingestion_status text not null default 'pending',
  ingestion_error text,
  created_at timestamptz not null default now(),
  constraint knowledge_documents_title_not_blank check (char_length(btrim(title)) > 0),
  constraint knowledge_documents_source_not_blank check (
    char_length(btrim(source_organization)) > 0
  ),
  constraint knowledge_documents_status_check check (
    ingestion_status in ('pending', 'processing', 'ready', 'failed')
  )
);

comment on table public.knowledge_documents is
  'Agricultural documents ingested for RAG. Prefer ICAR, IMD, KVK, state agricultural universities, and government extension publications.';

comment on column public.knowledge_documents.ingestion_status is
  'pending, processing, ready, or failed. Similarity search returns chunks only from ready documents.';

comment on column public.knowledge_documents.ingestion_error is
  'Operator-visible failure reason when ingestion_status is failed. Null otherwise.';

-- ---------------------------------------------------------------------------
-- knowledge_chunks
-- ---------------------------------------------------------------------------

create table public.knowledge_chunks (
  id uuid primary key default extensions.gen_random_uuid(),
  document_id uuid not null references public.knowledge_documents (id) on delete cascade,
  content text not null,
  embedding extensions.vector(1536) not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint knowledge_chunks_content_not_blank check (char_length(btrim(content)) > 0)
);

comment on table public.knowledge_chunks is
  'Document chunks and 1536-dimension embeddings. Deleting a document deletes its chunks. Past advisory JSON snapshots are not rewritten.';

comment on column public.knowledge_chunks.embedding is
  '1536-dimension embedding. Cosine distance. Must match the configured embedding model.';

comment on column public.knowledge_chunks.metadata is
  'Chunk metadata such as page_number and section. Document-level fields stay on knowledge_documents.';

-- ---------------------------------------------------------------------------
-- indexes
-- ---------------------------------------------------------------------------

create index knowledge_documents_crop_idx
  on public.knowledge_documents (crop);

create index knowledge_documents_disease_idx
  on public.knowledge_documents (disease);

create index knowledge_documents_region_idx
  on public.knowledge_documents (region);

create index knowledge_documents_status_idx
  on public.knowledge_documents (ingestion_status);

create index knowledge_chunks_document_id_idx
  on public.knowledge_chunks (document_id);

create index knowledge_chunks_embedding_hnsw_idx
  on public.knowledge_chunks
  using hnsw (embedding extensions.vector_cosine_ops);

-- ---------------------------------------------------------------------------
-- similarity search
-- Called by the backend with the service-role key:
--   rpc match_knowledge_chunks
-- similarity is cosine similarity (1 - cosine distance), not a calibrated probability.
-- Filters are case-insensitive exact matches. A null or blank filter is ignored.
-- match_count is clamped to 1..20.
-- ---------------------------------------------------------------------------

create or replace function public.match_knowledge_chunks(
  query_embedding extensions.vector(1536),
  match_count integer default 5,
  filter_crop text default null,
  filter_region text default null,
  filter_disease text default null
)
returns table (
  id uuid,
  document_id uuid,
  content text,
  metadata jsonb,
  similarity double precision,
  title text,
  source_organization text,
  document_url text,
  crop text,
  disease text,
  region text,
  publication_date date,
  chunk_created_at timestamptz
)
language sql
stable
security invoker
set search_path = public, extensions
as $$
  select
    c.id,
    c.document_id,
    c.content,
    c.metadata,
    (1 - (c.embedding <=> query_embedding))::double precision as similarity,
    d.title,
    d.source_organization,
    d.document_url,
    d.crop,
    d.disease,
    d.region,
    d.publication_date,
    c.created_at as chunk_created_at
  from public.knowledge_chunks as c
  inner join public.knowledge_documents as d
    on d.id = c.document_id
  where d.ingestion_status = 'ready'
    and (
      filter_crop is null
      or btrim(filter_crop) = ''
      or d.crop ilike btrim(filter_crop)
    )
    and (
      filter_region is null
      or btrim(filter_region) = ''
      or d.region ilike btrim(filter_region)
    )
    and (
      filter_disease is null
      or btrim(filter_disease) = ''
      or d.disease ilike btrim(filter_disease)
    )
  order by c.embedding <=> query_embedding
  limit least(greatest(coalesce(match_count, 5), 1), 20);
$$;

comment on function public.match_knowledge_chunks(
  extensions.vector(1536),
  integer,
  text,
  text,
  text
) is
  'Return the nearest ready knowledge chunks by cosine similarity. For backend service-role use only.';

-- Default privileges grant execute to public. Keep this RPC on the service role.
revoke all on function public.match_knowledge_chunks(
  extensions.vector(1536),
  integer,
  text,
  text,
  text
) from public;

revoke all on function public.match_knowledge_chunks(
  extensions.vector(1536),
  integer,
  text,
  text,
  text
) from anon, authenticated;

grant execute on function public.match_knowledge_chunks(
  extensions.vector(1536),
  integer,
  text,
  text,
  text
) to service_role;

-- ---------------------------------------------------------------------------
-- row level security
-- No policies. The service role bypasses RLS.
-- ---------------------------------------------------------------------------

alter table public.knowledge_documents enable row level security;
alter table public.knowledge_chunks enable row level security;
