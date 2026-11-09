# AgriSense AI — Supabase setup

These scripts create the database for the internal AgriSense AI app. They do not create the FastAPI or React application.

Run them in the Supabase SQL editor as the project owner. Run each migration once, in order. Re-running a table migration will fail because the tables already exist.

## Before you start

1. Open the Supabase project.
2. Go to **Database → Extensions** and enable **vector** if it is not already on.
3. Open **SQL Editor**.

`pgcrypto` is already installed on Supabase projects. The first migration still requests it in the `extensions` schema. If that statement reports that the extension already exists, continue with the next file. Later migrations call `extensions.gen_random_uuid()`.

## Run order

1. `migrations/20261109000001_extensions.sql`
2. `migrations/20261109000002_core_tables.sql`
3. `migrations/20261109000003_knowledge.sql`
4. `migrations/20261109000004_storage.sql`

`seed.sql` is optional. Every insert in it is commented out. Uncomment it only if you want three sample locations (Ludhiana, Nashik, Raipur). It does not insert weather, crops, or citations.

## What this creates

- `locations`, `crop_records`, `environmental_records`
- `advisory_records`, `chat_messages`, `alerts`
- `knowledge_documents`, `knowledge_chunks`
- `match_knowledge_chunks` for cosine similarity search
- Private Storage bucket `knowledge-documents` (50 MB; PDF, plain text, or Markdown)

Timestamps are `timestamptz` in UTC. Show them in Indian Standard Time (`Asia/Kolkata`) in the application. SQL does not convert the zone.

Row level security is enabled on every application table. There are no `anon` or `authenticated` policies. The FastAPI backend must use the service-role key, which bypasses RLS. Do not put that key, or the LLM API key, in the frontend.

`match_knowledge_chunks` can be executed only by `service_role`. Call it from the backend with `rpc`.

## Embedding size

`knowledge_chunks.embedding` is `vector(1536)`. That matches common models such as `text-embedding-3-small`. If you choose an embedding model with a different dimension, alter the column, the HNSW index, and the function argument before inserting chunks.

`similarity` in the function result is cosine similarity (`1 - cosine distance`). It is not a calibrated probability.

Search returns chunks only when the parent document has `ingestion_status = 'ready'`. Blank crop, region, or disease filters are ignored. A provided filter is a case-insensitive exact match on the document column. `match_count` is clamped between 1 and 20.

Page numbers and section labels belong in `knowledge_chunks.metadata`.

## Weather and alerts

Leave environmental measurements null when a provider does not return them. Do not store stand-in numbers.

Alert rows are created later by application rules. Those thresholds are configuration, not validated disease models. They are not stored in these scripts.

Deleting a crop keeps advisory, chat, and alert history by setting those foreign keys to null. Deleting a knowledge document deletes its chunks. `advisory_records.retrieved_sources` is a JSON snapshot, so old advisories keep the citations they stored.

## Checks

Growth stage: `seedling`, `vegetative`, `flowering`, `fruiting`, `maturity`, `harvest`.

Advisory type: `crop_management`, `disease_prevention`, `chatbot`, `alert_explanation`.

Chat role: `user`, `assistant`, `system`.

Alert category: `rainfall`, `temperature`, `humidity`, `soil_moisture`, `disease_symptoms`.

Alert severity: `info`, `low`, `moderate`, `high`.

Ingestion status: `pending`, `processing`, `ready`, `failed`.

## Confirm

```sql
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in (
    'locations',
    'crop_records',
    'environmental_records',
    'advisory_records',
    'chat_messages',
    'alerts',
    'knowledge_documents',
    'knowledge_chunks'
  )
order by table_name;

select proname
from pg_proc
where proname = 'match_knowledge_chunks';

select id, public, file_size_limit
from storage.buckets
where id = 'knowledge-documents';
```

Expect eight tables, one function, and one bucket with `public = false`.
