# AgriSense AI API

Base URL for local use: `http://127.0.0.1:8000`

Interactive schema: `/docs`

Timestamps are stored in UTC and also returned with an `_ist` field in `Asia/Kolkata`.

When `INTERNAL_API_TOKEN` is set, send `X-Internal-Token` on every `/api` route except `/api/health`.

Missing weather or soil values are JSON `null`. The response lists them in `unavailable_fields`. A failed refresh of cached weather sets `stale` to true. The API does not fill missing measurements.

## Health

`GET /api/health`

Returns provider names and whether the database, chat model, and embeddings are configured.

## Weather

`GET /api/weather/current?latitude=&longitude=`

`GET /api/weather/forecast?latitude=&longitude=`

`location_id` uses the stored coordinates instead. On a fresh current-weather read for a location, a snapshot is written to `environmental_records`. Cached reads are not written again. Optional `crop_id` links that snapshot to a crop.

Rainfall is the provider's precipitation amount in millimetres. Wind speed is kilometres per hour.

## Locations and crops

`POST /api/locations`

`GET /api/locations`

`GET /api/locations/{id}`

`POST /api/crops`

`GET /api/crops?location_id=`

`GET /api/crops/{id}`

`PUT /api/crops/{id}`

`DELETE /api/crops/{id}`

Growth stage is one of `seedling`, `vegetative`, `flowering`, `fruiting`, `maturity`, `harvest`.

## Environment

`POST /api/environment` stores an operator-entered snapshot. `source` is required. Leave unknown measurements out or null.

`GET /api/environment?location_id=&crop_id=&limit=`

## Advisory

`POST /api/advisory/crop` with `{ "crop_id": "..." }`

`POST /api/advisory/disease` with `{ "crop_id": "...", "symptoms": "..." }`

`GET /api/advisory/history?crop_id=&advisory_type=&date_from=&date_to=&limit=`

`GET /api/advisory/{id}`

The stored `advisory_response` includes crop, growth stage, advisory type, risk level, observations, possible concerns, recommendations, evidence, missing information, and limitations. Disease responses also include `disease_status`: `environmental_risk`, `suspected_from_symptoms`, or `not_assessed`.

Risk level is descriptive. Evidence is limited to documents retrieved for that request. Application rates in recommendations are removed.

## Chat

`POST /api/chat`

```json
{ "message": "When should I inspect paddy after humid weather?", "conversation_id": null, "crop_id": null }
```

`GET /api/chat/history/{conversation_id}`

A crop id adds that crop's location weather when the weather provider responds. References come from retrieved documents.

## Alerts

`GET /api/alerts?crop_id=&location_id=&unread_only=&limit=`

`POST /api/alerts/evaluate` with `location_id`, optional `crop_id`, and optional `symptoms`.

`PATCH /api/alerts/{id}/read`

Rules cover heavy rain, extreme temperature, high humidity on a configured crop list, low reported soil moisture, and reported symptoms. Each alert's `supporting_context` includes the threshold note.

## Knowledge

`POST /api/knowledge/upload` as multipart form data: `file`, `title`, `source_organization`, and optional `document_url`, `crop`, `disease`, `region`, `publication_date`.

PDF, plain text, or Markdown. Maximum 20 MB and 200 chunks. The private bucket `knowledge-documents` stores the file. `ingestion_status` becomes `ready` or `failed`.

`GET /api/knowledge`

`DELETE /api/knowledge/{id}`

Search uses `match_knowledge_chunks` and cosine similarity. Similarity is not shown to the model as a probability.
