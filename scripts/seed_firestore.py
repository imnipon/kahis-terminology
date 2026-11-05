#!/usr/bin/env python3
"""
scripts/seed_firestore.py
Uploads 190 KU custom synonyms from ku_custom_synonyms.csv to Cloud Firestore
using the standard Firestore REST API (no extra pip dependencies required).
"""

import csv
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

PROJECT_ID = "kahis-terminology"
API_KEY = "AIzaSyCn5jTgv0Kn2brpnRV8Lvf7XUbHh2_PZhc"
API_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents:commit?key={API_KEY}"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(SCRIPT_DIR)
CSV_PATH = os.path.join(APP_DIR, "ku_custom_synonyms.csv")

def seed():
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found.")
        sys.exit(1)

    writes = []
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        idx = 1
        for row in reader:
            cid = row["concept_id"].strip()
            text = row["ku_synonym_text"].strip()
            lang = row.get("lang_tag", "ku").strip()
            if not cid or not text:
                continue

            doc_id = f"ku_{cid}_{idx}"
            writes.append({
                "update": {
                    "name": f"projects/{PROJECT_ID}/databases/(default)/documents/ku_synonyms/{doc_id}",
                    "fields": {
                        "concept_id": {"stringValue": cid},
                        "synonym_text": {"stringValue": text},
                        "lang_tag": {"stringValue": lang},
                        "status": {"stringValue": "approved"},
                        "created_at": {"timestampValue": now_iso}
                    }
                }
            })
            idx += 1

    print(f"Prepared {len(writes)} records to upload to Firestore project '{PROJECT_ID}'...")

    req = urllib.request.Request(
        API_URL,
        data=json.dumps({"writes": writes}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            results = res_data.get("writeResults", [])
            print(f"SUCCESS! Successfully seeded {len(results)} synonyms into Firestore collection 'ku_synonyms'!")
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"HTTP Error {e.code}: {e.reason}")
        print(err_msg)
        print("\nNote: Please ensure Firestore Database is created in your Firebase Console and in 'test mode'.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    seed()
