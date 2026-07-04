"""
Structured data-catalog in SQLite, built from the YAML dictionaries.

This complements semantic RAG with *exact* lookups: "what columns does
fact_flights have?" or "which tables mention customer?" are answered by SQL,
not embeddings. Covers the 'SQL' + 'data dictionary / lineage' parts of the
project.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

import yaml

from config import settings


def _iter_catalog_files():
    for path in sorted(settings.kb_dir.rglob("*.yaml")):
        yield path
    for path in sorted(settings.kb_dir.rglob("*.yml")):
        yield path


def build_catalog() -> dict:
    settings.ensure_dirs()
    db = settings.catalog_db
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    con.executescript(
        """
        CREATE TABLE tables (
            warehouse TEXT, table_name TEXT, layer TEXT, grain TEXT,
            description TEXT, lineage TEXT
        );
        CREATE TABLE columns (
            warehouse TEXT, table_name TEXT, column_name TEXT,
            data_type TEXT, description TEXT
        );
        """
    )
    n_tables = n_cols = 0
    for path in _iter_catalog_files():
        doc = yaml.safe_load(path.read_text())
        if not isinstance(doc, dict) or "tables" not in doc:
            continue
        wh = doc.get("warehouse", path.stem)
        for tbl in doc["tables"]:
            con.execute(
                "INSERT INTO tables VALUES (?,?,?,?,?,?)",
                [wh, tbl.get("name"), tbl.get("layer"), tbl.get("grain"),
                 tbl.get("description"), tbl.get("lineage")],
            )
            n_tables += 1
            for col in tbl.get("columns", []):
                con.execute(
                    "INSERT INTO columns VALUES (?,?,?,?,?)",
                    [wh, tbl.get("name"), col.get("name"), col.get("type"), col.get("description")],
                )
                n_cols += 1
    con.commit()
    con.close()
    return {"tables": n_tables, "columns": n_cols}


# --- read helpers used by the API -------------------------------------------
def _connect():
    return sqlite3.connect(settings.catalog_db)


def get_table(table_name: str) -> Optional[dict]:
    if not settings.catalog_db.exists():
        return None
    con = _connect()
    try:
        row = con.execute(
            "SELECT warehouse, table_name, layer, grain, description, lineage "
            "FROM tables WHERE lower(table_name)=lower(?)", [table_name]
        ).fetchone()
        if not row:
            return None
        cols = con.execute(
            "SELECT column_name, data_type, description FROM columns "
            "WHERE lower(table_name)=lower(?)", [table_name]
        ).fetchall()
        return {
            "warehouse": row[0], "table": row[1], "layer": row[2], "grain": row[3],
            "description": row[4], "lineage": row[5],
            "columns": [{"name": c[0], "type": c[1], "description": c[2]} for c in cols],
        }
    finally:
        con.close()


def search_columns(term: str, limit: int = 25) -> list:
    if not settings.catalog_db.exists():
        return []
    con = _connect()
    try:
        rows = con.execute(
            "SELECT warehouse, table_name, column_name, data_type, description FROM columns "
            "WHERE column_name LIKE ? OR description LIKE ? LIMIT ?",
            [f"%{term}%", f"%{term}%", limit],
        ).fetchall()
        return [{"warehouse": r[0], "table": r[1], "column": r[2],
                 "type": r[3], "description": r[4]} for r in rows]
    finally:
        con.close()


def list_tables() -> list:
    if not settings.catalog_db.exists():
        return []
    con = _connect()
    try:
        rows = con.execute(
            "SELECT warehouse, table_name, layer, grain FROM tables ORDER BY warehouse, table_name"
        ).fetchall()
        return [{"warehouse": r[0], "table": r[1], "layer": r[2], "grain": r[3]} for r in rows]
    finally:
        con.close()
