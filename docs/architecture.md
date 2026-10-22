# Luther — architecture and case study

[Overview](../README.md) · [Verification](verification.md)

## Problem and audience

A specialized research workflow needs to keep articles organized by publication context while making their contents searchable. Summaries and possible research directions are useful only if a researcher can return to the source and distinguish evidence from inference.

Luther applies local software and optional AI to that workflow. It is a personal research tool, not a validated discovery engine or an enterprise research platform.

## Implementation choices

| Choice | Why it fits | Tradeoff |
| :--- | :--- | :--- |
| FastAPI plus a static browser interface | Keeps API and UI delivery together | Local application security still needs hardening before broader hosting |
| SQLite and FTS5 | Relational publication structure and full-text search without a database server | Current query handling and concurrency are sized for a small local workflow |
| Original PDFs retained locally | Lets a researcher compare analysis with source material | Requires storage management, access protection, and backup |
| Optional Ollama analysis | Keeps the core library usable without model inference | Output quality and hardware requirements vary; local does not mean accurate |
| Separate gap/inference labels | Makes uncertainty visible in the interface | Labels and prompts cannot substitute for broader literature verification |

## Data flow

The browser creates journal/issue records through the API. An upload is copied into local storage, PyMuPDF extracts available text, and basic metadata is inferred. SQLite stores the article and updates its FTS5 index through triggers.

If analysis is requested, the backend calls the local Ollama chat endpoint, parses the JSON response, and stores summaries/classifications/opportunities. Without inference, extracted articles remain `needs_analysis`. Search results and article detail views return to the same browser interface.

## Evidence boundaries

The repository demonstrates implementation structure, not measured research productivity or model accuracy. No throughput, cost-savings, publication impact, or enterprise deployment outcomes are asserted.

The screenshots show a working interface backed by synthetic records. They do not show actual research, generated findings, or successful model inference.

## Next engineering questions

- How should malformed model output be validated before it changes article metadata?
- How should larger or hostile uploads be bounded and isolated?
- How can source references be checked beyond prompt instructions?
- What recovery and regression checks are needed before depending on the tool long term?
