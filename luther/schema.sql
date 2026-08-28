CREATE TABLE IF NOT EXISTS journals (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  publisher TEXT NOT NULL DEFAULT '',
  issn TEXT NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '',
  website_url TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS volumes (
  id INTEGER PRIMARY KEY,
  journal_id INTEGER NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
  volume_number TEXT NOT NULL,
  year INTEGER,
  UNIQUE(journal_id, volume_number)
);

CREATE TABLE IF NOT EXISTS issues (
  id INTEGER PRIMARY KEY,
  volume_id INTEGER NOT NULL REFERENCES volumes(id) ON DELETE CASCADE,
  issue_number TEXT NOT NULL,
  publication_date TEXT,
  title TEXT NOT NULL DEFAULT '',
  issue_summary TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(volume_id, issue_number)
);

CREATE TABLE IF NOT EXISTS articles (
  id INTEGER PRIMARY KEY,
  issue_id INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  authors_json TEXT NOT NULL DEFAULT '[]',
  abstract TEXT NOT NULL DEFAULT '',
  publication_year INTEGER,
  publication_date TEXT,
  page_start TEXT,
  page_end TEXT,
  doi TEXT NOT NULL DEFAULT '',
  article_url TEXT NOT NULL DEFAULT '',
  pdf_path TEXT NOT NULL DEFAULT '',
  extracted_text TEXT NOT NULL DEFAULT '',
  generated_summary TEXT NOT NULL DEFAULT '',
  keywords_json TEXT NOT NULL DEFAULT '[]',
  period_name TEXT NOT NULL DEFAULT '',
  period_start INTEGER,
  period_end INTEGER,
  processing_status TEXT NOT NULL DEFAULT 'queued',
  processing_error TEXT NOT NULL DEFAULT '',
  full_text_source TEXT NOT NULL DEFAULT 'user_upload',
  access_type TEXT NOT NULL DEFAULT 'private',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS classifications (
  id INTEGER PRIMARY KEY,
  article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  category TEXT NOT NULL CHECK(category IN ('geography','theme','population','source','methodology')),
  value TEXT NOT NULL,
  confidence TEXT NOT NULL DEFAULT 'Medium' CHECK(confidence IN ('High','Medium','Low')),
  UNIQUE(article_id, category, value)
);

CREATE TABLE IF NOT EXISTS research_gaps (
  id INTEGER PRIMARY KEY,
  article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  gap_type TEXT NOT NULL,
  confidence TEXT NOT NULL DEFAULT 'Low' CHECK(confidence IN ('High','Medium','Low')),
  evidence TEXT NOT NULL DEFAULT '',
  page_reference TEXT NOT NULL DEFAULT '',
  section_reference TEXT NOT NULL DEFAULT '',
  suggested_direction TEXT NOT NULL DEFAULT '',
  verification_status TEXT NOT NULL DEFAULT 'Requires verification',
  saved INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS research_questions (
  id INTEGER PRIMARY KEY,
  question TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  confidence TEXT NOT NULL DEFAULT 'Low',
  status TEXT NOT NULL DEFAULT 'Idea',
  notes TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS article_search USING fts5(
  article_id UNINDEXED, title, authors, abstract, summary, extracted_text
);

CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
  INSERT INTO article_search(article_id,title,authors,abstract,summary,extracted_text)
  VALUES(new.id,new.title,new.authors_json,new.abstract,new.generated_summary,new.extracted_text);
END;
CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
  DELETE FROM article_search WHERE article_id=old.id;
  INSERT INTO article_search(article_id,title,authors,abstract,summary,extracted_text)
  VALUES(new.id,new.title,new.authors_json,new.abstract,new.generated_summary,new.extracted_text);
END;
CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
  DELETE FROM article_search WHERE article_id=old.id;
END;

