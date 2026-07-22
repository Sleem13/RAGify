# RAGify

RAGify is a local retrieval-augmented generation application for documents and spreadsheets. It supports grounded chat, page-level citations, durable background ingestion, spreadsheet analysis, dashboard generation, exports, English/Arabic layouts, and multiple LLM providers. Its Next.js interface uses an Ancient Egypt-inspired House of Knowledge design system.

## RAG pipeline

The backend follows clear SimpleRAG-style stages while preserving RAGify's features:

1. `services/document_processor.py` loads PDF, Office, image, text, and tabular files into metadata-rich chunks. PDF chunks retain page numbers.
2. `services/preprocessing.py` normalizes text for lexical retrieval while preserving multilingual content and negation.
3. `services/vector_db.py` persists MiniLM embeddings in FAISS and combines semantic and lexical scores.
4. `services/retrieval.py` selects diverse results, prepares numbered sources, validates history, and builds a grounded prompt.
5. `services/llm_manager.py` sends that prompt through the configured provider fallback chain.

The application layer is separated from the pipeline:

- `main.py` creates and configures FastAPI.
- `api/routers/` contains system, authentication, document, chat, and export endpoints.
- `core/config.py` owns environment-backed settings.
- `services/app_state.py` owns the thread-safe file registry and API-key state.
- `services/exporter.py` owns JSON, CSV, XLSX, and PDF exports.
- `services/ingestion.py` coordinates asynchronous extraction, embedding, registry commit, and rollback.
- `services/job_store.py` persists upload job status for frontend progress polling.

Uploads return HTTP 202 with a `job_id`. Poll `GET /jobs/{job_id}` until the status is `completed` or `failed`. The web interface handles this automatically.

## Requirements

- Python 3.11 or newer
- Node.js 20 or newer
- At least one provider key: `GEMINI_API_KEY` or `GROQ_API_KEY`

## Run locally

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Add your provider key(s) to `.env`, then start the backend:

```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 9999
```

To protect the API, set `RAGIFY_API_KEY` in `.env` to a long random value. The
Streamlit interface and backend both load this value, so no separate key entry is
needed when they run from the same checkout. Generate a suitable value with:

```powershell
python -c "import secrets; print('ragify-' + secrets.token_urlsafe(32))"
```

In a second PowerShell terminal, start the Next.js frontend:

```powershell
cd frontend
npm ci
npm run dev
```

Open:

- Frontend: http://localhost:3000
- Backend documentation: http://localhost:9999/docs
- Backend health endpoint: http://localhost:9999/

The frontend proxies `/api/backend` to `http://localhost:9999` by default. To use another backend, set `BACKEND_URL` before starting Next.js or enter a custom backend URL in the dashboard settings.

## Optional Streamlit interface

With the backend running:

```powershell
streamlit run app.py
```

The Streamlit app defaults to `http://localhost:9999`. Override it with `RAGIFY_BACKEND_URL` if needed.

### GitHub Codespaces

Create Codespaces secrets named `GEMINI_API_KEY` or `GROQ_API_KEY` and,
optionally, `RAGIFY_API_KEY`. Export them into the terminals that start the
backend and Streamlit, or copy `.env.example` to `.env` and fill in the same
values. When using a separately deployed backend, configure the identical
`RAGIFY_API_KEY` on that service and in the Streamlit environment.

## Verify changes

```powershell
python -m unittest discover -s tests -v
python evaluation\run_retrieval_eval.py
cd frontend
npm run lint
npm run build
```

## Local data

Uploaded content is indexed under `vectorstore/`, and file metadata is kept in `data/files_registry.json`. Ingestion jobs and hashed API keys are stored under `data/` but ignored by Git. Plain API keys are never persisted. Use the app's reset action only when you intentionally want to clear the index.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
