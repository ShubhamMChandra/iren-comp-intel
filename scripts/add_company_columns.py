"""
One-off migration: add missing columns to companies table if they don't exist.
Run from repo root: python3 scripts/add_company_columns.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import DATABASE_URL

db_path = DATABASE_URL.replace("sqlite:///", "")
if not Path(db_path).exists():
    print(f"Database not found: {db_path}")
    sys.exit(1)

import sqlite3
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("PRAGMA table_info(companies)")
existing = {row[1] for row in cur.fetchall()}

to_add = [
    ("ats_board", "VARCHAR(255)"),
    ("github_org", "VARCHAR(255)"),
    ("arxiv_org", "VARCHAR(255)"),
    ("embedding", "TEXT"),
    ("key_customers", "TEXT"),
    ("strengths", "TEXT"),
    ("weaknesses", "TEXT"),
    ("threat_level", "VARCHAR(20)"),
]
for col, typ in to_add:
    if col in existing:
        print(f"  {col} already exists")
    else:
        cur.execute(f"ALTER TABLE companies ADD COLUMN {col} {typ}")
        print(f"  added {col}")
conn.commit()
conn.close()
print("Done.")
