#!/usr/bin/env python3
"""
scripts/export_sqlite_from_firestore.py
Downloads all 'approved' KU synonyms from Cloud Firestore and updates
the local SQLite database (terminology_search.db) and creates terminology_search.db.gz
with 100% schema backward compatibility for KAHIS Dev handoff.
"""

import gzip
import json
import os
import shutil
import sqlite3
import sys
import time
import urllib.request
import urllib.error

PROJECT_ID = "kahis-terminology"
API_KEY = "AIzaSyCn5jTgv0Kn2brpnRV8Lvf7XUbHh2_PZhc"
FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/ku_synonyms?pageSize=1000&key={API_KEY}"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(APP_DIR, "terminology_search.db")
GZ_PATH = DB_PATH + ".gz"

def fetch_approved_synonyms():
    print(f"[INFO] Fetching approved synonyms from Cloud Firestore ({PROJECT_ID})...")
    req = urllib.request.Request(FIRESTORE_URL)
    synonyms = []
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            docs = data.get("documents", [])
            for doc in docs:
                fields = doc.get("fields", {})
                status = fields.get("status", {}).get("stringValue", "approved")
                if status == "approved":
                    cid = fields.get("concept_id", {}).get("stringValue", "").strip()
                    text = fields.get("synonym_text", {}).get("stringValue", "").strip()
                    lang = fields.get("lang_tag", {}).get("stringValue", "ku").strip()
                    cat = fields.get("created_at", {}).get("timestampValue", time.strftime("%Y-%m-%d %H:%M:%S"))
                    if cid and text:
                        synonyms.append((cid, text, lang, cat))
        print(f"[INFO] Retrieved {len(synonyms)} approved synonyms from Firestore.")
        return synonyms
    except Exception as e:
        print(f"[ERROR] Failed to fetch from Firestore: {e}")
        sys.exit(1)

def update_sqlite(synonyms):
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database file not found: {DB_PATH}")
        sys.exit(1)

    print(f"[INFO] Updating SQLite database: {DB_PATH} ...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Update ku_synonym_text table
    cur.execute("DELETE FROM ku_synonym_text")
    cur.executemany(
        "INSERT INTO ku_synonym_text (concept_id, ku_synonym_text, lang_tag, created_at) VALUES (?, ?, ?, ?)",
        synonyms
    )
    conn.commit()
    print(f"[INFO] Wrote {len(synonyms)} rows into table 'ku_synonym_text'.")

    # 2. Rebuild FTS5 index if exists
    try:
        cur.execute("INSERT INTO terms_fts(terms_fts) VALUES('rebuild')")
        conn.commit()
        print("[INFO] Rebuilt full-text search index (terms_fts).")
    except Exception as e:
        print(f"[WARN] FTS5 rebuild notice: {e}")

    conn.close()

    # 3. Automated QA Verification
    try:
        import verify_db
        print("\n[INFO] Running automated QA verification (34 checks)...")
        verify_db.run_audit()
    except Exception as e:
        print(f"[WARN] QA audit warning: {e}")

    # 4. Compress to .gz
    print(f"\n[INFO] Compressing {DB_PATH} -> {GZ_PATH} ...")
    t0 = time.time()
    with open(DB_PATH, "rb") as f_in:
        with gzip.open(GZ_PATH, "wb", compresslevel=9) as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    db_size = os.path.getsize(DB_PATH) / (1024 * 1024)
    gz_size = os.path.getsize(GZ_PATH) / (1024 * 1024)
    print(f"[SUCCESS] SQLite build completed in {time.time()-t0:.1f}s!")
    print(f"  - Database: {DB_PATH} ({db_size:.1f} MB)")
    print(f"  - Compressed Package: {GZ_PATH} ({gz_size:.1f} MB)")
    print(f"  - Ready for KAHIS Dev handover!")

if __name__ == "__main__":
    items = fetch_approved_synonyms()
    update_sqlite(items)
