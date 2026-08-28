from __future__ import annotations

import json
import os
import re
import shutil
import uuid
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .analyzer import analyze_with_ollama, basic_metadata, extract_pdf
from .db import ROOT, connect, initialize, json_value, row, rows, transaction

UPLOADS = ROOT / "data" / "uploads"
STATIC = ROOT / "static"
app = FastAPI(title="Luther", docs_url="/api/docs")


@app.on_event("startup")
def startup():
    UPLOADS.mkdir(parents=True, exist_ok=True)
    initialize()


def article_view(connection, article_id: int):
    article = row(connection, """SELECT a.*, i.issue_number, i.id issue_id, v.volume_number, v.id volume_id,
        j.name journal_name, j.id journal_id FROM articles a JOIN issues i ON i.id=a.issue_id
        JOIN volumes v ON v.id=i.volume_id JOIN journals j ON j.id=v.journal_id WHERE a.id=?""", (article_id,))
    if not article:
        raise HTTPException(404, "Article not found")
    article["authors"] = json_value(article.pop("authors_json"), [])
    article["keywords"] = json_value(article.pop("keywords_json"), [])
    article["classifications"] = rows(connection, "SELECT category,value,confidence FROM classifications WHERE article_id=? ORDER BY category,value", (article_id,))
    article["gaps"] = rows(connection, "SELECT * FROM research_gaps WHERE article_id=? ORDER BY id", (article_id,))
    article.pop("extracted_text", None)
    return article


@app.get("/api/dashboard")
def dashboard():
    with connect() as c:
        counts = row(c, """SELECT (SELECT count(*) FROM journals) journals, (SELECT count(*) FROM issues) issues,
            (SELECT count(*) FROM articles) articles, (SELECT count(*) FROM research_gaps) gaps""")
        recent = rows(c, """SELECT a.id,a.title,a.generated_summary,a.processing_status,a.created_at,j.name journal_name
            FROM articles a JOIN issues i ON i.id=a.issue_id JOIN volumes v ON v.id=i.volume_id
            JOIN journals j ON j.id=v.journal_id ORDER BY a.created_at DESC LIMIT 6""")
        gaps = rows(c, "SELECT id,title,gap_type,confidence,description,article_id FROM research_gaps ORDER BY created_at DESC LIMIT 6")
        questions = rows(c, "SELECT * FROM research_questions ORDER BY created_at DESC LIMIT 6")
        themes = rows(c, "SELECT value,count(*) count FROM classifications WHERE category='theme' GROUP BY value ORDER BY count DESC,value LIMIT 8")
        return {"counts": counts, "recent_articles": recent, "gaps": gaps, "questions": questions, "themes": themes}


@app.get("/api/library")
def library():
    with connect() as c:
        journals = rows(c, "SELECT * FROM journals ORDER BY name")
        for journal in journals:
            journal["volumes"] = rows(c, "SELECT * FROM volumes WHERE journal_id=? ORDER BY year DESC,volume_number DESC", (journal["id"],))
            for volume in journal["volumes"]:
                volume["issues"] = rows(c, """SELECT i.*,count(a.id) article_count FROM issues i LEFT JOIN articles a ON a.issue_id=i.id
                    WHERE i.volume_id=? GROUP BY i.id ORDER BY i.issue_number""", (volume["id"],))
        return journals


class JournalInput(BaseModel):
    name: str
    publisher: str = ""
    issn: str = ""
    description: str = ""
    website_url: str = ""


@app.post("/api/journals")
def create_journal(data: JournalInput):
    with transaction() as c:
        cursor = c.execute("INSERT INTO journals(name,publisher,issn,description,website_url) VALUES(?,?,?,?,?)", (data.name.strip(), data.publisher, data.issn, data.description, data.website_url))
        return {"id": cursor.lastrowid}


class IssueInput(BaseModel):
    journal_id: int
    volume_number: str
    issue_number: str
    year: int | None = None
    publication_date: str | None = None
    title: str = ""


@app.post("/api/issues")
def create_issue(data: IssueInput):
    with transaction() as c:
        c.execute("INSERT INTO volumes(journal_id,volume_number,year) VALUES(?,?,?) ON CONFLICT(journal_id,volume_number) DO UPDATE SET year=coalesce(excluded.year,year)", (data.journal_id, data.volume_number, data.year))
        volume = row(c, "SELECT id FROM volumes WHERE journal_id=? AND volume_number=?", (data.journal_id, data.volume_number))
        cursor = c.execute("INSERT INTO issues(volume_id,issue_number,publication_date,title) VALUES(?,?,?,?)", (volume["id"], data.issue_number, data.publication_date, data.title))
        return {"id": cursor.lastrowid}


@app.get("/api/issues/{issue_id}")
def issue_detail(issue_id: int):
    with connect() as c:
        issue = row(c, """SELECT i.*,v.volume_number,v.year,j.name journal_name,j.id journal_id FROM issues i
            JOIN volumes v ON v.id=i.volume_id JOIN journals j ON j.id=v.journal_id WHERE i.id=?""", (issue_id,))
        if not issue: raise HTTPException(404, "Issue not found")
        issue["articles"] = rows(c, "SELECT id,title,generated_summary,processing_status,authors_json FROM articles WHERE issue_id=? ORDER BY page_start,title", (issue_id,))
        for a in issue["articles"]: a["authors"] = json_value(a.pop("authors_json"), [])
        issue["distributions"] = {category: rows(c, """SELECT cl.value,count(*) count FROM classifications cl JOIN articles a ON a.id=cl.article_id
            WHERE a.issue_id=? AND cl.category=? GROUP BY cl.value ORDER BY count DESC,cl.value""", (issue_id, category)) for category in ("theme","geography","population","source","methodology")}
        issue["gaps"] = rows(c, "SELECT g.* FROM research_gaps g JOIN articles a ON a.id=g.article_id WHERE a.issue_id=?", (issue_id,))
        return issue


def safe_name(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._ -]", "_", Path(name).name)
    return f"{uuid.uuid4().hex[:10]}-{stem}"


def ingest_one(c, issue_id: int, source: Path, original_name: str, run_ai: bool, model: str):
    target = UPLOADS / safe_name(original_name)
    shutil.copy2(source, target)
    metadata = {"title": Path(original_name).stem, "authors": [], "abstract": "", "doi": ""}
    text = ""
    status, error = "extracted", ""
    try:
        text, _ = extract_pdf(target)
        metadata.update(basic_metadata(text, original_name))
    except Exception as exc:
        status, error = "failed", f"PDF extraction failed: {exc}"
    cursor = c.execute("""INSERT INTO articles(issue_id,title,authors_json,abstract,doi,pdf_path,extracted_text,processing_status,processing_error)
        VALUES(?,?,?,?,?,?,?,?,?)""", (issue_id, metadata["title"], json.dumps(metadata["authors"]), metadata["abstract"], metadata["doi"], str(target.relative_to(ROOT)), text, status, error))
    article_id = cursor.lastrowid
    if run_ai and text:
        try:
            result = analyze_with_ollama(text, model)
            apply_analysis(c, article_id, result)
        except Exception as exc:
            c.execute("UPDATE articles SET processing_status='needs_analysis',processing_error=? WHERE id=?", (f"Local AI unavailable: {exc}", article_id))
    elif text:
        c.execute("UPDATE articles SET processing_status='needs_analysis' WHERE id=?", (article_id,))
    return article_id


def apply_analysis(c, article_id: int, result: dict):
    period = result.get("period") or {}
    c.execute("""UPDATE articles SET title=?,authors_json=?,abstract=?,generated_summary=?,keywords_json=?,period_name=?,period_start=?,period_end=?,processing_status='complete',processing_error='' WHERE id=?""",
        (result.get("title") or "Untitled article", json.dumps(result.get("authors") or []), result.get("abstract") or "", result.get("summary") or "", json.dumps(result.get("keywords") or []), period.get("name") or "", period.get("start_year"), period.get("end_year"), article_id))
    c.execute("DELETE FROM classifications WHERE article_id=?", (article_id,))
    mapping = {"geographies":"geography","themes":"theme","populations":"population","sources_used":"source","methodologies":"methodology"}
    for source_key, category in mapping.items():
        for value in result.get(source_key) or []:
            if isinstance(value, str) and value.strip(): c.execute("INSERT OR IGNORE INTO classifications(article_id,category,value) VALUES(?,?,?)", (article_id, category, value.strip()))
    c.execute("DELETE FROM research_gaps WHERE article_id=?", (article_id,))
    valid_types = {"Author-Identified Gap", "Article Limitation", "Potential AI-Inferred Gap"}
    for gap in result.get("gaps") or []:
        gap_type = gap.get("gap_type") if gap.get("gap_type") in valid_types else "Potential AI-Inferred Gap"
        confidence = gap.get("confidence") if gap.get("confidence") in {"High","Medium","Low"} else "Low"
        c.execute("""INSERT INTO research_gaps(article_id,title,description,gap_type,confidence,evidence,page_reference,section_reference,suggested_direction)
            VALUES(?,?,?,?,?,?,?,?,?)""", (article_id,gap.get("title") or "Potential research opportunity",gap.get("description") or "",gap_type,confidence,gap.get("evidence") or "",gap.get("page_reference") or "",gap.get("section_reference") or "",gap.get("suggested_direction") or ""))


@app.post("/api/issues/{issue_id}/upload")
async def upload(issue_id: int, files: list[UploadFile] = File(...), analyze: bool = Form(False), model: str = Form("qwen3:8b")):
    temp = UPLOADS / f"tmp-{uuid.uuid4().hex}"
    temp.mkdir(parents=True)
    created = []
    try:
        with transaction() as c:
            if not row(c, "SELECT id FROM issues WHERE id=?", (issue_id,)): raise HTTPException(404, "Issue not found")
            for uploaded in files:
                saved = temp / safe_name(uploaded.filename or "article.pdf")
                with saved.open("wb") as output: shutil.copyfileobj(uploaded.file, output)
                candidates = []
                if zipfile.is_zipfile(saved):
                    extract_dir = temp / uuid.uuid4().hex
                    extract_dir.mkdir()
                    with zipfile.ZipFile(saved) as archive:
                        for member in archive.infolist():
                            if member.filename.lower().endswith(".pdf") and not member.is_dir():
                                member.filename = Path(member.filename).name
                                archive.extract(member, extract_dir)
                                candidates.append((extract_dir / member.filename, member.filename))
                elif saved.suffix.lower() == ".pdf": candidates.append((saved, uploaded.filename or saved.name))
                else: raise HTTPException(400, "Only PDF and ZIP files are supported")
                for path, name in candidates: created.append(ingest_one(c, issue_id, path, name, analyze, model))
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    return {"article_ids": created}


@app.post("/api/articles/{article_id}/analyze")
def analyze(article_id: int, model: str = "qwen3:8b"):
    with transaction() as c:
        article = row(c, "SELECT extracted_text FROM articles WHERE id=?", (article_id,))
        if not article: raise HTTPException(404, "Article not found")
        if not article["extracted_text"]: raise HTTPException(400, "No extracted text is available")
        try: result = analyze_with_ollama(article["extracted_text"], model)
        except Exception as exc: raise HTTPException(503, f"Could not reach local Ollama: {exc}")
        apply_analysis(c, article_id, result)
        return article_view(c, article_id)


@app.get("/api/articles/{article_id}")
def article(article_id: int):
    with connect() as c: return article_view(c, article_id)


@app.get("/api/articles/{article_id}/pdf")
def article_pdf(article_id: int):
    with connect() as c: article = row(c, "SELECT pdf_path FROM articles WHERE id=?", (article_id,))
    if not article: raise HTTPException(404, "Article not found")
    path = (ROOT / article["pdf_path"]).resolve()
    if ROOT not in path.parents or not path.exists(): raise HTTPException(404, "PDF not found")
    return FileResponse(path, media_type="application/pdf")


@app.get("/api/search")
def search(q: str = "", theme: str = "", geography: str = "", gap_type: str = ""):
    with connect() as c:
        sql = """SELECT DISTINCT a.id,a.title,a.generated_summary,a.processing_status,a.authors_json,j.name journal_name,v.volume_number,i.issue_number
            FROM articles a JOIN issues i ON i.id=a.issue_id JOIN volumes v ON v.id=i.volume_id JOIN journals j ON j.id=v.journal_id"""
        joins, where, params = [], [], []
        if q.strip(): joins.append(" JOIN article_search s ON s.article_id=a.id"); where.append("article_search MATCH ?"); params.append(q.strip().replace('"',''))
        if theme: joins.append(" JOIN classifications ct ON ct.article_id=a.id AND ct.category='theme'"); where.append("ct.value=?"); params.append(theme)
        if geography: joins.append(" JOIN classifications cg ON cg.article_id=a.id AND cg.category='geography'"); where.append("cg.value=?"); params.append(geography)
        if gap_type: joins.append(" JOIN research_gaps rg ON rg.article_id=a.id"); where.append("rg.gap_type=?"); params.append(gap_type)
        sql += "".join(joins) + ((" WHERE " + " AND ".join(where)) if where else "") + " ORDER BY a.created_at DESC LIMIT 100"
        results = rows(c, sql, params)
        for item in results: item["authors"] = json_value(item.pop("authors_json"), [])
        facets = {category: rows(c, "SELECT DISTINCT value FROM classifications WHERE category=? ORDER BY value", (category,)) for category in ("theme","geography")}
        return {"results": results, "facets": facets}


class QuestionInput(BaseModel):
    question: str
    description: str = ""
    confidence: str = "Low"
    status: str = "Idea"
    notes: str = ""


@app.post("/api/questions")
def save_question(data: QuestionInput):
    with transaction() as c:
        cursor = c.execute("INSERT INTO research_questions(question,description,confidence,status,notes) VALUES(?,?,?,?,?)", (data.question,data.description,data.confidence,data.status,data.notes))
        return {"id": cursor.lastrowid}


app.mount("/assets", StaticFiles(directory=STATIC), name="assets")


@app.get("/{path:path}")
def spa(path: str):
    return FileResponse(STATIC / "index.html")

