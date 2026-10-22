# Luther — agent instructions

Local research library for medieval-history journal articles: PDF/ZIP ingestion, text extraction, SQLite full-text search, and optional local Ollama analysis. Architecture: `docs/architecture.md`. Verification: `docs/verification.md`.

## Stack and commands (Windows)
- Python 3.12, code in `luther/` (`main.py`, `db.py`, `analyzer.py`, `schema.sql`), browser UI in `static/`.
- Install: `.\install.ps1` (creates `.venv`, installs pinned `requirements.txt`). Run: `.\start.ps1` → http://127.0.0.1:8000.
- Ollama is optional; ingestion and search must keep working without it.

## Domain rules
- Core principle: an omission in one article is not evidence of a gap in the wider literature. Keep author-identified gaps, article limitations and AI-inferred gaps clearly separated and labeled.
- AI output is a starting point for review, never a verified scholarly finding.

## Working conventions
- Branch per change. There is no automated test suite yet; when adding behavior, add tests (pytest) and document verification steps in `docs/verification.md`.
- Never commit `data/` contents with real articles or personal research; demo material must be synthetic.
- Public repo: no personal data or local paths.
