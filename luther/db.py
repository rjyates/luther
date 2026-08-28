from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "luther.db"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def transaction():
    connection = connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize() -> None:
    with transaction() as connection:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def rows(connection: sqlite3.Connection, query: str, params=()) -> list[dict]:
    return [dict(row) for row in connection.execute(query, params).fetchall()]


def row(connection: sqlite3.Connection, query: str, params=()) -> dict | None:
    result = connection.execute(query, params).fetchone()
    return dict(result) if result else None


def json_value(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default

