# Contributing to RAGify

## Development setup

Follow the local Python and Node.js setup in [README.md](README.md). Run the FastAPI backend on port 9999 and the Next.js frontend on port 3000.

## Pull requests

1. Create a branch from `main`.
2. Keep retrieval, application state, API routing, and UI concerns in their existing modules.
3. Add or update tests when behavior changes.
4. Update documentation when an API or setup step changes.
5. Run the backend tests, frontend linter, and frontend production build.

Python code should follow PEP 8. TypeScript code should pass the repository ESLint configuration.

Bug reports should include reproduction steps, expected behavior, actual behavior, and relevant logs without secrets or uploaded document contents.
