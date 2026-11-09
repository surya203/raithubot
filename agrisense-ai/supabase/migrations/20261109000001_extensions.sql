-- AgriSense AI
-- 1 of 4. Run this file first in the Supabase SQL editor.
--
-- pgcrypto supplies gen_random_uuid().
-- pgvector stores knowledge-chunk embeddings.
-- Both live in the extensions schema, which is the Supabase default.

create extension if not exists pgcrypto with schema extensions;
create extension if not exists vector with schema extensions;
