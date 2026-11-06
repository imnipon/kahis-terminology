#!/usr/bin/env python3
"""
scripts/build_search_db.py
Builds SQLite database (terminology_search.db) with FTS5 Full-Text Search
and SNOMED CT relationship tables for the SNOMED CT Browser Web Application.
"""

import sqlite3
import csv
import glob
import time
import os
import sys

def main():
    start_time = time.time()
    db_file = 'terminology_search.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    print("==================================================")
    print("Building SQLite Search Database: terminology_search.db")
    print("==================================================")

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # 1. Create main terms table
    print("\n[1/4] Creating tables...")
    cursor.execute("""
    CREATE TABLE terms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        display_name TEXT,
        in_sapdt TEXT,
        in_vsct TEXT,
        in_sct_inter TEXT,
        sapdt_concept_id TEXT,
        sapdt_status TEXT,
        sapdt_change_type TEXT,
        sapdt_description_id TEXT,
        sapdt_fsn TEXT,
        sapdt_preferred TEXT,
        sapdt_acceptable TEXT,
        synonym TEXT,
        sapdt_semantic_type TEXT,
        snomed_concept_id TEXT,
        snomed_fsn TEXT,
        snomed_preferred_term TEXT,
        snomed_all_synonyms TEXT,
        snomed_active TEXT,
        snomed_module TEXT,
        snomed_semantic_type TEXT,
        body_system TEXT,
        snomed_definition_status TEXT,
        snomed_parent_concepts TEXT,
        match_type TEXT,
        concept_count TEXT,
        all_snomed_concept_ids TEXT,
        replacement_concept_id TEXT,
        match_confidence TEXT,
        updated_at TEXT,
        updated_by TEXT,
        created_at TEXT
    );
    """)

    # Index for fast concept_id lookups
    cursor.execute("CREATE INDEX idx_snomed_cid ON terms (snomed_concept_id);")
    cursor.execute("CREATE INDEX idx_sapdt_cid ON terms (sapdt_concept_id);")
    cursor.execute("CREATE INDEX idx_semantic_type ON terms (snomed_semantic_type);")
    cursor.execute("CREATE INDEX idx_body_system ON terms (body_system);")

    # 2. Create FTS5 virtual table
    cursor.execute("""
    CREATE VIRTUAL TABLE terms_fts USING fts5(
        term_id UNINDEXED,
        display_name,
        synonym,
        snomed_fsn,
        snomed_preferred_term,
        sapdt_fsn,
        snomed_concept_id,
        sapdt_concept_id,
        body_system,
        snomed_semantic_type,
        content='terms',
        content_rowid='id'
    );
    """)

    # 3. Insert data from terminology_master_31cols.csv
    print("[2/4] Importing terminology_master_31cols.csv into SQLite...")
    input_csv = 'terminology_master_31cols.csv'
    if not os.path.exists(input_csv):
        print(f"ERROR: {input_csv} does not exist!")
        sys.exit(1)

    with open(input_csv, encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)

        placeholders = ', '.join(['?'] * len(header))
        sql = f"INSERT INTO terms ({', '.join(header)}) VALUES ({placeholders})"

        rows_to_insert = []
        count = 0
        for row in reader:
            rows_to_insert.append(row)
            count += 1
            if len(rows_to_insert) >= 5000:
                cursor.executemany(sql, rows_to_insert)
                rows_to_insert = []

        if rows_to_insert:
            cursor.executemany(sql, rows_to_insert)

    print(f"  Inserted {count} rows into 'terms' table.")

    # Populate FTS5 table
    print("  Populating FTS5 index...")
    cursor.execute("""
    INSERT INTO terms_fts (rowid, term_id, display_name, synonym, snomed_fsn, snomed_preferred_term, sapdt_fsn, snomed_concept_id, sapdt_concept_id, body_system, snomed_semantic_type)
    SELECT id, id, display_name, synonym, snomed_fsn, snomed_preferred_term, sapdt_fsn, snomed_concept_id, sapdt_concept_id, body_system, snomed_semantic_type
    FROM terms;
    """)

    # 4. Build Relationships Table for Hierarchy Tree Views & Concept Attributes
    print("[3/4] Building relationships & concepts tables from RF2...")
    cursor.execute("""
    CREATE TABLE relationships (
        source_id TEXT,
        destination_id TEXT,
        type_id TEXT,
        type_name TEXT,
        source_release TEXT
    );
    """)
    cursor.execute("CREATE INDEX idx_rel_src ON relationships (source_id);")
    cursor.execute("CREATE INDEX idx_rel_dst ON relationships (destination_id);")

    cursor.execute("""
    CREATE TABLE concept_terms (
        concept_id TEXT PRIMARY KEY,
        term TEXT,
        semantic_type TEXT
    );
    """)

    # Discover RF2 files
    vet_rel = glob.glob('SnomedCT_VETExtension_PRODUCTION_*/Snapshot/Terminology/sct2_Relationship_Snapshot*.txt')[0]
    inter_rel = glob.glob('SnomedCT_InternationalRF2_PRODUCTION_*/Snapshot/Terminology/sct2_Relationship_Snapshot*.txt')[0]
    vet_desc = glob.glob('SnomedCT_VETExtension_PRODUCTION_*/Snapshot/Terminology/sct2_Description_Snapshot-en*.txt')[0]
    inter_desc = glob.glob('SnomedCT_InternationalRF2_PRODUCTION_*/Snapshot/Terminology/sct2_Description_Snapshot-en*.txt')[0]

    # Load FSNs for concept_terms
    c_terms = []
    seen_cids = set()
    # SCT-02 FIX: VSCT (vet_desc) must be processed FIRST — higher priority than SCT International
    # Old (wrong): [inter_desc, vet_desc] → SCT-Inter terms filled seen_cids first, VSCT was ignored
    # New (correct): [vet_desc, inter_desc] → VSCT fills first, SCT-Inter only adds what's missing
    for desc_path in [vet_desc, inter_desc]:
        with open(desc_path, encoding='utf-8') as f:
            f.readline()
            for line in f:
                parts = line.rstrip('\r\n').split('\t')
                if len(parts) > 7 and parts[2] == '1' and parts[6] == '900000000000003001':
                    cid = parts[4]
                    if cid not in seen_cids:
                        seen_cids.add(cid)
                        term = parts[7]
                        stype = ''
                        if '(' in term and term.endswith(')'):
                            stype = term[term.rfind('(')+1:-1]
                        c_terms.append((cid, term, stype))
                        if len(c_terms) >= 10000:
                            cursor.executemany("INSERT OR IGNORE INTO concept_terms VALUES (?, ?, ?)", c_terms)
                            c_terms = []
    if c_terms:
        cursor.executemany("INSERT OR IGNORE INTO concept_terms VALUES (?, ?, ?)", c_terms)

    # Insert Active Relationships
    rel_names = {
        '116680003': 'Is a',
        '363698007': 'Finding site',
        '363704007': 'Procedure site',
        '405813007': 'Procedure site - Direct',
        '405814008': 'Procedure site - Indirect',
        '272741003': 'Associated morphology',
        '246075003': 'Causative agent',
        '363700003': 'Direct morphology',
        '363699004': 'Between',
        '260686004': 'Method',
        '363714003': 'Interprets',
    }

    rel_rows = []
    for rel_path, tag in [(vet_rel, 'VSCT'), (inter_rel, 'SCT_Inter')]:
        with open(rel_path, encoding='utf-8') as f:
            f.readline()
            for line in f:
                parts = line.rstrip('\r\n').split('\t')
                if len(parts) > 7 and parts[2] == '1':
                    src, dst, type_id = parts[4], parts[5], parts[7]
                    type_name = rel_names.get(type_id, 'Attribute')
                    rel_rows.append((src, dst, type_id, type_name, tag))
                    if len(rel_rows) >= 20000:
                        cursor.executemany("INSERT INTO relationships VALUES (?, ?, ?, ?, ?)", rel_rows)
                        rel_rows = []
    if rel_rows:
        cursor.executemany("INSERT INTO relationships VALUES (?, ?, ?, ?, ?)", rel_rows)

    # Commit and Optimize
    print("[4/4] Optimizing database and indices...")
    conn.commit()
    cursor.execute("PRAGMA optimize;")
    conn.close()

    db_size = os.path.getsize(db_file) / (1024 * 1024)
    print("\n==================================================")
    print("SUCCESS: Search Database Built!")
    print("==================================================")
    print(f"Database File: {db_file}")
    print(f"Database Size: {db_size:.2f} MB")
    print(f"Elapsed Time : {time.time() - start_time:.2f} seconds")

if __name__ == '__main__':
    main()
