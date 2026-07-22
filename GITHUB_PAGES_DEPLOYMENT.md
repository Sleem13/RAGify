# Deploy the RAGify frontend to GitHub Pages

GitHub Pages hosts the static Next.js frontend. The FastAPI backend must remain
on Render or another Python host.

## One-time repository setup

1. Open the GitHub repository and go to **Settings → Pages**.
2. Under **Build and deployment**, set **Source** to **GitHub Actions**.
3. Go to **Settings → Secrets and variables → Actions → Variables**.
4. Add a repository variable named `NEXT_PUBLIC_API_URL` whose value is the
   public HTTPS URL of the FastAPI backend, for example:

   `https://your-ragify-api.onrender.com`

5. In the Render backend settings, set `FRONTEND_URL` to the GitHub Pages
   origin:

   `https://sleem13.github.io`

## Deploy

Push to the `main` branch, or open **Actions → Deploy frontend to GitHub
Pages → Run workflow**.

After a successful deployment, the site is available at:

`https://sleem13.github.io/RAGify/`

The workflow is defined in `.github/workflows/deploy-pages.yml`.
