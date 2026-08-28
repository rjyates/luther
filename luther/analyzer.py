from __future__ import annotations

import json
import re
from typing import Any

SYSTEM_PROMPT = """You are Luther, a careful medieval-history research analyst. Analyze only the supplied article text. Never turn an omission in one article into a literature-wide gap. Return strict JSON matching the requested shape. Evidence excerpts must be short, faithfully quoted, and include a page number when visible. Use careful labels: Author-Identified Gap, Article Limitation, or Potential AI-Inferred Gap. Potential inferences require broader literature verification."""

SCHEMA = {
    "title": "string", "authors": ["string"], "abstract": "string",
    "summary": "1-3 short paragraphs", "keywords": ["string"],
    "period": {"name": "string", "start_year": "integer|null", "end_year": "integer|null"},
    "geographies": ["string"], "themes": ["string"], "populations": ["string"],
    "sources_used": ["string"], "methodologies": ["string"],
    "gaps": [{"title": "string", "description": "string", "gap_type": "string", "confidence": "High|Medium|Low", "evidence": "string", "page_reference": "string", "section_reference": "string", "suggested_direction": "string"}]
}


def extract_pdf(path) -> tuple[str, list[dict[str, Any]]]:
    import fitz
    document = fitz.open(path)
    pages = []
    chunks = []
    for number, page in enumerate(document, start=1):
        text = page.get_text("text").strip()
        pages.append({"page": number, "text": text})
        chunks.append(f"\n--- PAGE {number} ---\n{text}")
    return "".join(chunks).strip(), pages


def basic_metadata(text: str, filename: str) -> dict[str, Any]:
    lines = [line.strip() for line in text[:8000].splitlines() if line.strip()]
    title = next((line for line in lines[:25] if 20 <= len(line) <= 240 and not line.lower().startswith(("abstract", "doi", "volume"))), filename.rsplit(".", 1)[0])
    abstract = ""
    match = re.search(r"(?is)\babstract\b\s*[:.—-]?\s*(.{100,2000}?)(?:\n\s*(?:keywords?|introduction|1[.\s]))", text[:18000])
    if match:
        abstract = re.sub(r"\s+", " ", match.group(1)).strip()
    doi_match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", text[:15000], re.I)
    return {"title": title, "authors": [], "abstract": abstract, "doi": doi_match.group(0).rstrip(".,)") if doi_match else ""}


def analyze_with_ollama(text: str, model: str, base_url: str = "http://127.0.0.1:11434") -> dict[str, Any]:
    import httpx
    prompt = f"Return one JSON object shaped like:\n{json.dumps(SCHEMA)}\n\nARTICLE TEXT:\n{text[:120000]}"
    response = httpx.post(f"{base_url}/api/chat", json={
        "model": model,
        "stream": False,
        "format": "json",
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        "options": {"temperature": 0.1}
    }, timeout=600)
    response.raise_for_status()
    return json.loads(response.json()["message"]["content"])
