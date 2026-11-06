#!/usr/bin/env python3
"""
scripts/export_sqlite_from_firestore.py
Downloads 'approved' KU synonyms from Cloud Firestore, merges them into
the local SQLite database (terminology_search.db) without deleting existing synonyms,
rotates sources/4_KU-Custom/ku_synonym_text_YYYYMMDD.csv (archiving older dates to archive/legacy_data/),
and updates db_metadata.
"""

import csv
import glob
import gzip
import json
import os
import shutil
import sqlite3
import sys
import time
import urllib.request
import urllib.error

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

PROJECT_ID = "kahis-terminology"
API_KEY = "AIzaSyCn5jTgv0Kn2brpnRV8Lvf7XUbHh2_PZhc"
FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/ku_synonyms?pageSize=1000&key={API_KEY}"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(APP_DIR, "terminology_search.db")
GZ_PATH = DB_PATH + ".gz"
SOURCES_DIR = os.path.join(APP_DIR, "sources")
ARCHIVE_DATA_DIR = os.path.join(APP_DIR, "archive", "legacy_data")

def fetch_approved_synonyms():
    print(f"[INFO] กำลังดึงรายการคำพ้องที่อนุมัติแล้ว (status='approved') จาก Cloud Firestore ({PROJECT_ID})...")
    req = urllib.request.Request(FIRESTORE_URL)
    synonyms = []
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            docs = data.get("documents", [])
            for doc in docs:
                fields = doc.get("fields", {})
                status = fields.get("status", {}).get("stringValue", "pending")
                if status == "approved":
                    cid = fields.get("concept_id", {}).get("stringValue", "").strip()
                    text = fields.get("synonym_text", {}).get("stringValue", "").strip()
                    lang = fields.get("lang_tag", {}).get("stringValue", "ku").strip()
                    cat = (
                        fields.get("created_at", {}).get("stringValue")
                        or fields.get("created_at", {}).get("timestampValue")
                        or time.strftime("%Y-%m-%d %H:%M:%S")
                    )
                    if cid and text:
                        synonyms.append((cid, text, lang, cat))
        print(f"[INFO] พบรายการ Approved บน Cloud Firestore ทั้งหมด: {len(synonyms)} รายการ")
        return synonyms
    except Exception as e:
        print(f"[ERROR] ไม่สามารถเชื่อมต่อ Cloud Firestore: {e}")
        sys.exit(1)

def rotate_and_write_ku_csv(conn):
    ku_ver = time.strftime("%Y%m%d")
    ku_dir = os.path.join(SOURCES_DIR, "4_KU-Custom")
    os.makedirs(ku_dir, exist_ok=True)
    os.makedirs(ARCHIVE_DATA_DIR, exist_ok=True)

    target_csv = os.path.join(ku_dir, f"ku_synonym_text_{ku_ver}.csv")

    # Archive older ku_synonym_text_*.csv files in sources/4_KU-Custom/
    for old_csv in glob.glob(os.path.join(ku_dir, "ku_synonym_text_*.csv")):
        if os.path.abspath(old_csv) != os.path.abspath(target_csv):
            dst = os.path.join(ARCHIVE_DATA_DIR, os.path.basename(old_csv))
            if os.path.exists(dst):
                os.remove(dst)
            shutil.move(old_csv, dst)
            print(f"[INFO] ย้ายไฟล์เวอร์ชันเก่าไปเก็บที่ archive/legacy_data/{os.path.basename(old_csv)}")

    cur = conn.cursor()
    cur.execute("""
        SELECT k.id, k.concept_id, COALESCE(t.display_name, ''), COALESCE(t.snomed_fsn, ''),
               k.ku_synonym_text, k.lang_tag, k.created_at
        FROM ku_synonym_text k
        LEFT JOIN terms t ON (t.snomed_concept_id = k.concept_id OR t.sapdt_concept_id = k.concept_id)
        ORDER BY k.id
    """)
    rows = cur.fetchall()
    with open(target_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "concept_id", "display_name", "snomed_fsn", "ku_synonym_text", "lang_tag", "created_at"])
        writer.writerows(rows)

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='db_metadata'")
    if cur.fetchone():
        cur.execute("INSERT OR REPLACE INTO db_metadata (meta_key, meta_value) VALUES (?, ?)", ("ku_version", ku_ver))
        cur.execute("INSERT OR REPLACE INTO db_metadata (meta_key, meta_value) VALUES (?, ?)", ("ku_badge", f"KU {ku_ver}"))
        cur.execute("INSERT OR REPLACE INTO db_metadata (meta_key, meta_value) VALUES (?, ?)", ("ku_file", os.path.basename(target_csv)))
        conn.commit()
    print(f"[INFO] อัปเดตไฟล์คำพ้องเวอร์ชันล่าสุด: sources/4_KU-Custom/{os.path.basename(target_csv)} (รวม {len(rows)} รายการ)")

def update_sqlite(synonyms):
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] ไม่พบไฟล์ฐานข้อมูล: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    added_count = 0
    for cid, text, lang, cat in synonyms:
        cur.execute(
            "SELECT id FROM ku_synonym_text WHERE concept_id = ? AND LOWER(ku_synonym_text) = LOWER(?)",
            (cid, text)
        )
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO ku_synonym_text (concept_id, ku_synonym_text, lang_tag, created_at) VALUES (?, ?, ?, ?)",
                (cid, text, lang, cat)
            )
            added_count += 1

    conn.commit()
    total_ku = cur.execute("SELECT COUNT(*) FROM ku_synonym_text").fetchone()[0]
    print(f"[INFO] เพิ่มคำพ้องใหม่ลง SQLite สำเร็จ: +{added_count} รายการ (รวมในฐานข้อมูลทั้งหมด {total_ku} รายการ)")

    rotate_and_write_ku_csv(conn)
    conn.close()
    print("[SUCCESS] ซิงก์ข้อมูลคำพ้องจาก Cloud Firestore ลง SQLite และอัปเดตไฟล์เวอร์ชันสำเร็จ!")

if __name__ == "__main__":
    items = fetch_approved_synonyms()
    update_sqlite(items)
