-- AgriSense AI
-- 4 of 4. Run after 20261109000003_knowledge.sql.
--
-- Private bucket for agricultural PDFs and text files.
-- No public read policy is created. The FastAPI backend uploads with the service-role key.
-- storage.objects already has row level security. With no policy, anon and authenticated cannot read or write objects.

insert into storage.buckets (
  id,
  name,
  public,
  file_size_limit,
  allowed_mime_types
)
values (
  'knowledge-documents',
  'knowledge-documents',
  false,
  52428800,
  array[
    'application/pdf',
    'text/plain',
    'text/markdown'
  ]
)
on conflict (id) do nothing;
