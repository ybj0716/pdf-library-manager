import sqlite3
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = Path.home() / ".pdf_manager" / "library.db"


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL UNIQUE,
            title TEXT DEFAULT '',
            authors TEXT DEFAULT '',
            year INTEGER,
            journal TEXT DEFAULT '',
            doi TEXT DEFAULT '',
            abstract TEXT DEFAULT '',
            keywords TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            category TEXT DEFAULT '',
            date_added TEXT,
            metadata_source TEXT DEFAULT ''
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def add_paper(paper: Dict[str, Any]) -> int:
    conn = get_connection()
    c = conn.cursor()
    paper = dict(paper)
    paper.setdefault('date_added', datetime.now().isoformat())
    paper.setdefault('tags', '')
    paper.setdefault('category', '')
    paper.setdefault('metadata_source', '')
    for key in ['title','authors','journal','doi','abstract','keywords']:
        paper.setdefault(key, '')
    paper.setdefault('year', None)
    try:
        c.execute("""
            INSERT OR REPLACE INTO papers
            (filename, filepath, title, authors, year, journal, doi, abstract,
             keywords, tags, category, date_added, metadata_source)
            VALUES (:filename, :filepath, :title, :authors, :year, :journal,
                    :doi, :abstract, :keywords, :tags, :category,
                    :date_added, :metadata_source)
        """, paper)
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()


def get_paper(paper_id: int) -> Optional[Dict]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM papers WHERE id = ?", (paper_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_papers(search: str = "", category: str = "", tag: str = "") -> List[Dict]:
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT * FROM papers WHERE 1=1"
    params = []
    if search:
        query += " AND (title LIKE ? OR authors LIKE ? OR journal LIKE ? OR keywords LIKE ? OR doi LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s, s, s])
    if category and category != "전체":
        query += " AND category = ?"
        params.append(category)
    if tag:
        query += " AND tags LIKE ?"
        params.append(f"%{tag}%")
    query += " ORDER BY year DESC NULLS LAST, title ASC"
    c.execute(query, params)
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows


def update_paper(paper_id: int, updates: Dict[str, Any]):
    if not updates:
        return
    conn = get_connection()
    c = conn.cursor()
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    c.execute(f"UPDATE papers SET {set_clause} WHERE id = ?",
              list(updates.values()) + [paper_id])
    conn.commit()
    conn.close()


def delete_paper(paper_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
    conn.commit()
    conn.close()


def get_categories() -> List[str]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT DISTINCT category FROM papers WHERE category != '' ORDER BY category")
    result = [row[0] for row in c.fetchall()]
    conn.close()
    return result


def get_all_tags() -> List[str]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT tags FROM papers WHERE tags != ''")
    all_tags = set()
    for row in c.fetchall():
        for tag in row[0].split(","):
            t = tag.strip()
            if t:
                all_tags.add(t)
    conn.close()
    return sorted(all_tags)


def get_stats() -> Dict[str, int]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM papers")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM papers WHERE title != ''")
    with_meta = c.fetchone()[0]
    conn.close()
    return {"total": total, "with_metadata": with_meta}


def get_setting(key: str, default: str = "") -> str:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(key: str, value: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()
