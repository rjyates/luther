# Luther

Luther is a private, local medieval-history research library. It organizes uploaded journal PDFs as **Journal → Volume → Issue → Article**, extracts their text, and can use a local Ollama model to produce structured summaries, classifications, limitations, and carefully qualified research opportunities.

There are no subscriptions, cloud services, user accounts, or paid APIs. The PDFs, extracted text, and database stay on the computer running Luther.

## The simple setup

Luther needs only:

1. [Python 3.12](https://www.python.org/downloads/) — free and required.
2. [Ollama](https://ollama.com/) — free and optional, but required for automatic summaries and classification.

On Windows, open PowerShell in this folder and run:

```powershell
.\install.ps1
.\start.ps1
```

The first command creates a private Python environment inside this folder and installs the PDF/web libraries. The second starts Luther at <http://127.0.0.1:8000>. Nothing is exposed to the internet or the local network.

For local AI analysis, install Ollama and run once:

```powershell
ollama pull qwen3:8b
```

The model download is several gigabytes. A computer with at least 16 GB of RAM is recommended for this model. PDF upload and text extraction work without Ollama; those articles will show **Needs analysis** until Ollama is available.

## First workflow

1. Create a journal.
2. Add a volume and issue.
3. Open the issue and upload one PDF, multiple PDFs, or one ZIP containing PDFs.
4. Select **Analyze now with local Ollama**, or analyze each article later.
5. Review the summary, classification, source evidence, and cautiously worded research opportunities.

Luther never treats an omission in one article as proof of a gap in the wider scholarly literature. AI-inferred opportunities are labeled provisional and require verification.

## Moving Luther to another computer

Copy this entire folder to the other Windows computer, including the `data` folder. Then run `install.ps1` on that computer. The portable collection consists of:

- `data/luther.db` — all metadata and analysis.
- `data/uploads/` — private original PDFs.

Do not share the `data` folder publicly; uploaded articles may be copyrighted.

## Backups

Stop Luther, then copy the entire `data` folder to a private backup drive. Restoring that folder restores the collection.

## Project layout

- `luther/main.py` — local API and ingestion workflow.
- `luther/schema.sql` — SQLite data model and full-text search.
- `luther/analyzer.py` — PDF extraction and optional Ollama analysis.
- `static/` — the scholarly desktop-first interface.
- `data/` — local database and private uploads (not committed to Git).

API documentation is available locally at <http://127.0.0.1:8000/api/docs> while Luther is running.

