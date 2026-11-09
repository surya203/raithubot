# AgriSense AI

Internal agricultural advisory API and React dashboard.

## Backend

The API loads `backend/.env` when that file exists. Values in it override the process environment. With `LLM_PROVIDER` left blank, chat uses `GROQ_API_KEY` and the model `openai/gpt-oss-20b`. `LLM_PROVIDER=openai` uses `LLM_API_KEY` or `OPENAI_API_KEY`, with `gpt-4.1-mini` unless `LLM_MODEL` is set. Embeddings use OpenAI `text-embedding-3-small` (1536 dimensions) so they match the database column.

Weather by latitude and longitude works without Supabase. Open-Meteo is the weather provider and does not need a key.

### Run

From `agrisense-ai/backend`, with Python 3.11:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The venv inherits the shell environment. `backend/.env` supplies Supabase, the model choice, and the internal token. Do not commit that file. `.env.example` lists every setting.

- Interactive docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/api/health

Health reports which integrations are configured. It does not return keys.

For an internal deployment, set `INTERNAL_API_TOKEN`. Clients then send `X-Internal-Token`. `/api/health` stays open.

### Tests

```powershell
python -m pytest
```

### Database

Run the SQL files in `supabase/migrations` in order before starting the data-backed routes. See `supabase/README.md`.

Alert thresholds in the environment file are operational heuristics. They are not calibrated disease models or official IMD warnings.

## Frontend

From `agrisense-ai/frontend`:

```powershell
npm install
npm run dev
```

Open http://127.0.0.1:5173. The dev server proxies `/api` to the backend and attaches `X-Internal-Token` from `backend/.env`. The token is not placed in the page bundle. Leave `VITE_API_BASE_URL` blank for this local setup. Start the backend first.
