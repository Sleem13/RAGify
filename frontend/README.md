# RAGify frontend

This directory contains the Next.js interface for RAGify.

Start the FastAPI backend on port 9999 first. Then run:

```powershell
npm ci
npm run dev
```

Open http://localhost:3000. In local development, Next.js proxies `/api/backend` to `BACKEND_URL`, which defaults to `http://localhost:9999`.

Quality checks:

```powershell
npm run lint
npm run build
```
