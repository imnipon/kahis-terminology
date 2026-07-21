#!/usr/bin/env python3
"""
build_direct_db.py
==================
สร้าง terminology_search.db โดยตรงจาก 3 แหล่งข้อมูลต้นฉบับ:
  1. SA-PDT-Terminology-XX/          (SA-PDT release TXT files)
  2. SnomedCT_VETExtension_*/        (VSCT RF2 Snapshot)
  3. SnomedCT_InternationalRF2_*/    (SCT International RF2 Snapshot)

กฏ:
  - ห้ามแก้ไขไฟล์ต้นฉบับทุกไฟล์ (Read-Only raw datasets)
  - Priority: SA-PDT > VSCT > SCT-International
  - IS-A relationship type_id = 116680003 (SNOMED CT มาตรฐาน)
  - Active logic: SA-PDT Active OR VSCT Active

Usage:
  python3 scripts/build_direct_db.py
  python3 scripts/build_direct_db.py --dry-run   (ตรวจสอบโดยไม่สร้าง DB)

สำหรับ Admin UI: server.py จะเรียกสคริปต์นี้ผ่าน subprocess
"""

import os
import sys
import glob
import csv
import re
import sqlite3
import time

# ---------------------------------------------------------------------------
# Path resolution — ใช้ __file__ เพื่อให้ทำงานได้ทุก drive/user
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR    = os.path.dirname(SCRIPT_DIR)               # kahis-terminology-app/
KAHIS_DIR  = os.path.dirname(APP_DIR)                  # kahis-terminology/
DB_OUT     = os.path.join(APP_DIR, 'terminology_search.db')
DB_TEMP    = DB_OUT + '.building'

IS_A_TYPE  = '116680003'   # SNOMED CT IS-A relationship (ถูกต้อง ลงท้าย 3)
PRIMITIVE  = '900000000000074008'
FULLY_DEF  = '900000000000073002'

DRY_RUN = '--dry-run' in sys.argv

# ---------------------------------------------------------------------------
# Logging — print ทุกบรรทัดด้วย flush เพื่อให้ stream ไปที่ admin UI ได้
# ---------------------------------------------------------------------------
def log(msg, tag='INFO'):
    print(f'[{tag}] {msg}', flush=True)


# ---------------------------------------------------------------------------
# Auto-detect source folders
# ---------------------------------------------------------------------------
def find_sources():
    sapdt_dirs = sorted(glob.glob(os.path.join(KAHIS_DIR, 'SA-PDT*')))
    vsct_dirs  = sorted(glob.glob(os.path.join(KAHIS_DIR, 'SnomedCT_VETExtension_*')))
    sct_dirs   = sorted(glob.glob(os.path.join(KAHIS_DIR, 'SnomedCT_InternationalRF2_*')))
    return (
        sapdt_dirs[-1]  if sapdt_dirs  else None,
        vsct_dirs[-1]   if vsct_dirs   else None,
        sct_dirs[-1]    if sct_dirs    else None,
    )


# ---------------------------------------------------------------------------
# Find RF2 Snapshot files
# ---------------------------------------------------------------------------
def find_rf2(base_dir, pattern):
    hits = glob.glob(os.path.join(base_dir, '**', pattern), recursive=True)
    return hits[0] if hits else None


def open_tsv(path):
    """Open RF2 TSV file as DictReader."""
    return csv.DictReader(open(path, encoding='utf-8'), delimiter='\t')


# ---------------------------------------------------------------------------
# Read SA-PDT release file
# ---------------------------------------------------------------------------
def read_sapdt(sapdt_dir):
    """
    SA-PDT release file is DESCRIPTION-LEVEL (one row per term, not per concept).
    Columns: Status | Concept Identifier | Description Identifier | Description Term | Term Designation
    Term Designation values: Preferred | Acceptable | FSN
    Active status: concept is Active if ANY of its rows is Active.

    Returns dict: concept_id → row dict
    """
    rel_files = sorted(glob.glob(os.path.join(sapdt_dir, 'SA-PDTReleaseFile_full_*.txt')))
    if not rel_files:
        rel_files = sorted(glob.glob(os.path.join(sapdt_dir, '*.txt')))
    if not rel_files:
        log(f'SA-PDT release file not found in {sapdt_dir}', 'WARN')
        return {}

    rel_file = rel_files[-1]  # latest release
    log(f'SA-PDT: {os.path.basename(rel_file)}')

    # Aggregate: concept_id → {status, preferred, fsn, synonyms[]}
    agg = {}
    with open(rel_file, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter='\t')
        log(f'SA-PDT columns: {reader.fieldnames}')
        for row in reader:
            cid  = (row.get('Concept Identifier') or '').strip()
            if not cid:
                continue
            status   = (row.get('Status') or 'Active').strip()
            term     = (row.get('Description Term') or '').strip()
            desig    = (row.get('Term Designation') or 'Acceptable').strip()
            desc_id  = (row.get('Description Identifier') or '').strip()

            if cid not in agg:
                agg[cid] = {
                    'status': 'Inactive',  # upgraded to Active if any row is Active
                    'preferred': '',
                    'fsn': '',
                    'synonyms': [],
                    'desc_ids': [],
                }

            # Active wins over Inactive (OR logic)
            if status == 'Active':
                agg[cid]['status'] = 'Active'

            if desc_id:
                agg[cid]['desc_ids'].append(desc_id)

            if desig == 'Preferred':
                agg[cid]['preferred'] = term
            elif desig == 'FSN':
                agg[cid]['fsn'] = term
            elif desig in ('Acceptable', 'Synonym'):
                if term not in agg[cid]['synonyms']:
                    agg[cid]['synonyms'].append(term)

    records = {}
    for cid, a in agg.items():
        preferred = a['preferred'] or a['fsn']
        fsn       = a['fsn'] or a['preferred']
        synonyms  = ' | '.join(a['synonyms'])

        records[cid] = {
            'sapdt_concept_id':       cid,
            'sapdt_status':           a['status'],
            'sapdt_change_type':      '',
            'sapdt_description_id':   ' | '.join(a['desc_ids']),
            'sapdt_fsn':              fsn,
            'sapdt_preferred':        preferred,
            'sapdt_acceptable':       synonyms,
            'sapdt_semantic_type':    '',
            'snomed_concept_id':      cid,   # SA-PDT Concept Identifier = SNOMED concept ID
            'match_type':             'sapdt',
            'match_confidence':       '',
            'replacement_concept_id': '',
            'concept_count':          '1',
            'all_snomed_concept_ids': cid,
            'snomed_fsn':             '',
            'snomed_preferred_term':  '',
            'snomed_all_synonyms':    '',
            'snomed_active':          'No',
            'snomed_module':          '',
            'snomed_semantic_type':   '',
            'snomed_definition_status': PRIMITIVE,
            'body_system':            '',
            'snomed_parent_concepts': '',
            'in_sapdt':               'Yes',
            'in_vsct':                'No',
            'in_sct_inter':           'No',
            'display_name':           preferred or fsn or cid,
        }

    log(f'SA-PDT: {len(records):,} concepts loaded (aggregated from description-level file)')
    return records


# ---------------------------------------------------------------------------
# Read VSCT / SCT-Inter descriptions (RF2 Snapshot)
# ---------------------------------------------------------------------------
def read_rf2_descriptions(desc_path, lang='en'):
    """
    Returns dict: concept_id → {fsn, preferred, synonyms[], active, module}
    Only processes active descriptions with type 900000000000003001 (FSN)
    or 900000000000013009 (Synonym).
    Note: VSCT file may be -es suffix but still contains English terms internally.
    """
    import sys
    # Fix Bug 2: SCT International has fields > 131072 bytes
    csv.field_size_limit(min(sys.maxsize, 10 * 1024 * 1024))  # 10 MB

    FSN_TYPE = '900000000000003001'
    SYN_TYPE = '900000000000013009'

    concepts = {}
    log(f'  Reading: {os.path.basename(desc_path)}')

    with open(desc_path, encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('active') != '1':
                continue
            # Accept ALL language codes — VSCT uses 'es' but terms are still valid
            # (lang filter removed: was causing 0 results for VSCT)

            cid   = row.get('conceptId', '').strip()
            dtype = row.get('typeId', '').strip()
            term  = row.get('term', '').strip()
            mid   = row.get('moduleId', '').strip()

            if not cid or not term:
                continue

            if cid not in concepts:
                concepts[cid] = {
                    'fsn': '', 'preferred': '', 'synonyms': [],
                    'active': '1', 'module': mid
                }

            if dtype == FSN_TYPE:
                concepts[cid]['fsn'] = term
            elif dtype == SYN_TYPE:
                concepts[cid]['synonyms'].append(term)

    return concepts


# ---------------------------------------------------------------------------
# Read VSCT / SCT-Inter concepts (active status, definition status)
# ---------------------------------------------------------------------------
def read_rf2_concepts(concept_path):
    """Returns dict: concept_id → {active, definition_status, module}"""
    result = {}
    log(f'  Reading: {os.path.basename(concept_path)}')
    with open(concept_path, encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            cid = row.get('id', '').strip()
            if not cid:
                continue
            result[cid] = {
                'active':            row.get('active', '1').strip(),
                'definition_status': row.get('definitionStatusId', PRIMITIVE).strip(),
                'module':            row.get('moduleId', '').strip(),
            }
    return result


# ---------------------------------------------------------------------------
# Read relationships (IS-A hierarchy)
# ---------------------------------------------------------------------------
def read_rf2_relationships(rel_path, source='sct'):
    """Returns list of (source_id, destination_id, type_id, type_name, source)"""
    result = []
    log(f'  Reading: {os.path.basename(rel_path)}')
    with open(rel_path, encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('active') != '1':
                continue
            result.append((
                row.get('sourceId', '').strip(),
                row.get('destinationId', '').strip(),
                row.get('typeId', '').strip(),
                '',          # type_name — filled separately
                source
            ))
    log(f'  Relationships: {len(result):,}')
    return result


# ---------------------------------------------------------------------------
# Main Build
# ---------------------------------------------------------------------------
def build():
    t0 = time.time()
    log('=' * 60)
    log('KAHIS Terminology DB Builder v1.0')
    log('=' * 60)

    # --- Locate sources ---
    sapdt_dir, vsct_dir, sct_dir = find_sources()
    if not sapdt_dir:
        log('SA-PDT folder not found! aborting.', 'ERROR')
        sys.exit(1)
    if not vsct_dir:
        log('VSCT folder not found! aborting.', 'ERROR')
        sys.exit(1)
    if not sct_dir:
        log('SCT International folder not found! aborting.', 'ERROR')
        sys.exit(1)

    log(f'SA-PDT:  {os.path.basename(sapdt_dir)}')
    log(f'VSCT:    {os.path.basename(vsct_dir)}')
    log(f'SCT:     {os.path.basename(sct_dir)}')
    log('')

    if DRY_RUN:
        log('DRY-RUN mode — ไม่สร้าง DB', 'WARN')
        log('Source detection OK. Exiting dry-run.')
        return

    # --- Read SA-PDT ---
    log('Step 1/6: อ่าน SA-PDT...')
    sapdt = read_sapdt(sapdt_dir)

    # --- Read VSCT descriptions ---
    log('Step 2/6: อ่าน VSCT descriptions...')
    # FIX-01: บังคับใช้ไฟล์ภาษาอังกฤษ (-en) เป็น primary เพื่อป้องกัน glob เลือกไฟล์ภาษาสเปน (-es)
    # glob.glob() ไม่รับประกัน sort order — ระบุ -en pattern โดยตรงเพื่อความแน่นอน
    vsct_desc_path = (
        find_rf2(vsct_dir, 'sct2_Description_Snapshot-en*.txt') or
        find_rf2(vsct_dir, 'sct2_Description_Snapshot*.txt')
    )
    vsct_conc_path = find_rf2(vsct_dir, 'sct2_Concept_Snapshot*.txt')
    vsct_rel_path  = find_rf2(vsct_dir, 'sct2_Relationship_Snapshot*.txt')

    if not all([vsct_desc_path, vsct_conc_path, vsct_rel_path]):
        log(f'VSCT files incomplete. Found: desc={vsct_desc_path}, conc={vsct_conc_path}, rel={vsct_rel_path}', 'ERROR')
        sys.exit(1)

    log(f'  VSCT desc file: {os.path.basename(vsct_desc_path)}')
    vsct_descs  = read_rf2_descriptions(vsct_desc_path)
    vsct_concs  = read_rf2_concepts(vsct_conc_path)
    vsct_rels   = read_rf2_relationships(vsct_rel_path, 'vsct')

    # --- Read SCT International descriptions ---
    log('Step 3/6: อ่าน SCT International descriptions...')
    sct_desc_path = find_rf2(sct_dir, 'sct2_Description_Snapshot*.txt')
    sct_conc_path = find_rf2(sct_dir, 'sct2_Concept_Snapshot*.txt')
    sct_rel_path  = find_rf2(sct_dir, 'sct2_Relationship_Snapshot*.txt')

    if not all([sct_desc_path, sct_conc_path, sct_rel_path]):
        log(f'SCT files incomplete.', 'ERROR')
        sys.exit(1)

    sct_descs = read_rf2_descriptions(sct_desc_path)
    sct_concs = read_rf2_concepts(sct_conc_path)
    sct_rels  = read_rf2_relationships(sct_rel_path, 'sct')

    # --- Merge: SA-PDT + VSCT + SCT ---
    log('Step 4/6: Merge ข้อมูล...')

    # 4a. Merge SA-PDT + VSCT + SCT info
    # Priority: SCT-Int English > VSCT-en English > SA-PDT own terms
    # Active status from VSCT concept table
    for sapdt_cid, rec in sapdt.items():
        snomed_cid = rec['snomed_concept_id']

        if snomed_cid in vsct_concs:
            rec['in_vsct'] = 'Yes'
        if snomed_cid in sct_descs:
            rec['in_sct_inter'] = 'Yes'

        # FIX-03: English FSN/Preferred from SCT-Int with fallback to VSCT-en
        # (VSCT Extension concepts may not be in SCT-Int)
        sct_desc  = sct_descs.get(snomed_cid) or {}
        vsct_desc = vsct_descs.get(snomed_cid) or {}
        best_desc = sct_desc if sct_desc.get('fsn') else vsct_desc
        if best_desc.get('fsn'):
            rec['snomed_fsn']            = best_desc.get('fsn', '')
            rec['snomed_preferred_term'] = best_desc.get('preferred', '') or best_desc.get('fsn', '')
            rec['snomed_module']         = best_desc.get('module', '')
            vsct_syns = vsct_desc.get('synonyms', [])
            all_syns  = sct_desc.get('synonyms', []) + vsct_syns
            rec['snomed_all_synonyms']   = ' | '.join(all_syns)

        # Extract semantic type from FSN tag e.g. (disorder), (finding)
        fsn_tag_src = rec.get('snomed_fsn') or rec.get('sapdt_fsn') or ''
        sem_match = re.search(r'\(([^)]+)\)$', fsn_tag_src)
        if sem_match:
            rec['snomed_semantic_type'] = sem_match.group(1)

        # Active status: VSCT concept table preferred, fallback SCT
        conc_src = vsct_concs.get(snomed_cid) or sct_concs.get(snomed_cid)
        if conc_src:
            rec['snomed_active']            = 'Yes' if conc_src['active'] == '1' else 'No'
            rec['snomed_definition_status'] = conc_src['definition_status']

        # display_name: SA-PDT preferred > SNOMED English preferred > SA-PDT FSN
        rec['display_name'] = (
            rec['sapdt_preferred'] or
            rec.get('snomed_preferred_term', '') or
            rec['sapdt_fsn'] or sapdt_cid
        )

    # 4b. VSCT-only concepts (not in SA-PDT)
    # FIX-02: English terms from SCT-Int with fallback to VSCT-en
    # (VSCT Extension-specific concepts won't exist in SCT-Int)
    vsct_only_added = 0
    seen_sapdt_cids = {r['snomed_concept_id'] for r in sapdt.values()}

    for snomed_cid in vsct_concs:
        if snomed_cid in seen_sapdt_cids:
            continue

        conc_src    = vsct_concs.get(snomed_cid, {})
        active_flag = 'Yes' if conc_src.get('active') == '1' else 'No'

        # FIX-02: Fallback ไป vsct_descs เมื่อไม่พบใน sct_descs
        sct_desc  = sct_descs.get(snomed_cid, {})
        vsct_desc = vsct_descs.get(snomed_cid, {})
        fsn       = sct_desc.get('fsn', '') or vsct_desc.get('fsn', '')
        preferred = (sct_desc.get('preferred', '') or sct_desc.get('fsn', '') or
                     vsct_desc.get('preferred', '') or vsct_desc.get('fsn', ''))
        vsct_syns = vsct_desc.get('synonyms', [])
        all_syns  = sct_desc.get('synonyms', []) + vsct_syns

        sem_match = re.search(r'\(([^)]+)\)$', fsn)
        sem_type  = sem_match.group(1) if sem_match else ''

        key = f'vsct_{snomed_cid}'
        sapdt[key] = {
            'sapdt_concept_id':       '',
            'sapdt_status':           '',
            'sapdt_change_type':      '',
            'sapdt_description_id':   '',
            'sapdt_fsn':              '',
            'sapdt_preferred':        '',
            'sapdt_acceptable':       '',
            'sapdt_semantic_type':    '',
            'snomed_concept_id':      snomed_cid,
            'match_type':             'vsct_only',
            'match_confidence':       '',
            'replacement_concept_id': '',
            'concept_count':          '1',
            'all_snomed_concept_ids': snomed_cid,
            'snomed_fsn':             fsn,
            'snomed_preferred_term':  preferred,
            'snomed_all_synonyms':    ' | '.join(all_syns),
            'snomed_active':          active_flag,
            'snomed_module':          conc_src.get('module', ''),
            'snomed_semantic_type':   sem_type,
            'snomed_definition_status': conc_src.get('definition_status', PRIMITIVE),
            'body_system':            '',
            'snomed_parent_concepts': '',
            'in_sapdt':               'No',
            'in_vsct':                'Yes',
            'in_sct_inter':           'Yes' if snomed_cid in sct_descs else 'No',
            'display_name':           preferred or fsn or snomed_cid,
        }
        vsct_only_added += 1
        seen_sapdt_cids.add(snomed_cid)

    log(f'SA-PDT concepts: {len([r for r in sapdt.values() if r["in_sapdt"]=="Yes"]):,}')
    log(f'VSCT-only added: {vsct_only_added:,}')
    log(f'Total records:   {len(sapdt):,}')

    # --- Build relationships table ---
    log('Step 5/6: สร้างตาราง relationships...')
    all_rels = vsct_rels + sct_rels
    # Build concept_id → term lookup for type_name
    all_descs_combined = {**sct_descs, **vsct_descs}  # VSCT overrides SCT
    for i, (src, dst, tid, _, src_tag) in enumerate(all_rels):
        type_info = all_descs_combined.get(tid)
        type_name = ''
        if type_info:
            type_name = type_info.get('preferred', '') or type_info.get('fsn', '')
        all_rels[i] = (src, dst, tid, type_name, src_tag)

    # --- Write DB ---
    log('Step 6/6: เขียน DB...')

    if os.path.exists(DB_TEMP):
        os.remove(DB_TEMP)

    conn = sqlite3.connect(DB_TEMP)
    cur = conn.cursor()

    # Create terms table
    cur.execute('''CREATE TABLE terms (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        display_name            TEXT,
        in_sapdt                TEXT DEFAULT "No",
        in_vsct                 TEXT DEFAULT "No",
        in_sct_inter            TEXT DEFAULT "No",
        sapdt_concept_id        TEXT,
        sapdt_status            TEXT,
        sapdt_change_type       TEXT,
        sapdt_description_id    TEXT,
        sapdt_fsn               TEXT,
        sapdt_preferred         TEXT,
        sapdt_acceptable        TEXT,
        synonym                 TEXT,
        sapdt_semantic_type     TEXT,
        snomed_concept_id       TEXT,
        snomed_fsn              TEXT,
        snomed_preferred_term   TEXT,
        snomed_all_synonyms     TEXT,
        snomed_active           TEXT DEFAULT "No",
        snomed_module           TEXT,
        snomed_semantic_type    TEXT,
        body_system             TEXT,
        snomed_definition_status TEXT DEFAULT "900000000000074008",
        snomed_parent_concepts  TEXT,
        match_type              TEXT,
        concept_count           TEXT,
        all_snomed_concept_ids  TEXT,
        replacement_concept_id  TEXT,
        match_confidence        TEXT,
        updated_at              TEXT DEFAULT "",
        updated_by              TEXT DEFAULT "",
        created_at              TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Create relationships table
    cur.execute('''CREATE TABLE relationships (
        source_id      TEXT,
        destination_id TEXT,
        type_id        TEXT,
        type_name      TEXT,
        source_release TEXT
    )''')

    # Create concept_terms table (for fast parent/child lookup)
    cur.execute('''CREATE TABLE concept_terms (
        concept_id   TEXT PRIMARY KEY,
        term         TEXT,
        semantic_type TEXT
    )''')

    # Create ku_synonym_text table
    cur.execute('''CREATE TABLE ku_synonym_text (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        concept_id      TEXT NOT NULL,
        ku_synonym_text TEXT NOT NULL,
        lang_tag        TEXT DEFAULT "ku",
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # Insert terms
    rows_inserted = 0
    for rec in sapdt.values():
        cur.execute('''INSERT INTO terms (
            display_name, in_sapdt, in_vsct, in_sct_inter,
            sapdt_concept_id, sapdt_status, sapdt_change_type, sapdt_description_id,
            sapdt_fsn, sapdt_preferred, sapdt_acceptable, synonym, sapdt_semantic_type,
            snomed_concept_id, snomed_fsn, snomed_preferred_term, snomed_all_synonyms,
            snomed_active, snomed_module, snomed_semantic_type, body_system,
            snomed_definition_status, snomed_parent_concepts, match_type,
            concept_count, all_snomed_concept_ids, replacement_concept_id, match_confidence
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
            rec.get('display_name',''),
            rec.get('in_sapdt','No'),
            rec.get('in_vsct','No'),
            rec.get('in_sct_inter','No'),
            rec.get('sapdt_concept_id',''),
            rec.get('sapdt_status',''),
            rec.get('sapdt_change_type',''),
            rec.get('sapdt_description_id',''),
            rec.get('sapdt_fsn',''),
            rec.get('sapdt_preferred',''),
            rec.get('sapdt_acceptable',''),
            rec.get('sapdt_acceptable',''),   # synonym = acceptable synonyms
            rec.get('sapdt_semantic_type',''),
            rec.get('snomed_concept_id',''),
            rec.get('snomed_fsn',''),
            rec.get('snomed_preferred_term',''),
            rec.get('snomed_all_synonyms',''),
            rec.get('snomed_active','No'),
            rec.get('snomed_module',''),
            rec.get('snomed_semantic_type',''),
            rec.get('body_system',''),
            rec.get('snomed_definition_status', PRIMITIVE),
            rec.get('snomed_parent_concepts',''),
            rec.get('match_type',''),
            rec.get('concept_count','1'),
            rec.get('all_snomed_concept_ids',''),
            rec.get('replacement_concept_id',''),
            rec.get('match_confidence',''),
        ))
        rows_inserted += 1

    log(f'  terms: {rows_inserted:,} rows inserted')

    # Insert relationships (deduplicate by source+dest+type)
    seen_rels = set()
    rel_count = 0
    for (src, dst, tid, tname, stag) in all_rels:
        key = (src, dst, tid)
        if key in seen_rels:
            continue
        seen_rels.add(key)
        cur.execute('INSERT INTO relationships VALUES (?,?,?,?,?)',
                    (src, dst, tid, tname, stag))
        rel_count += 1
    log(f'  relationships: {rel_count:,} rows inserted')

    # Insert concept_terms (VSCT first = higher priority per SCT-02 fix)
    seen_cterms = set()
    ct_count = 0
    for cid, d in {**sct_descs, **vsct_descs}.items():  # vsct overrides sct
        if cid in seen_cterms:
            continue
        seen_cterms.add(cid)
        fsn = d.get('fsn', '')
        sem_match = re.search(r'\(([^)]+)\)$', fsn)
        sem = sem_match.group(1) if sem_match else ''
        cur.execute('INSERT OR IGNORE INTO concept_terms VALUES (?,?,?)', (cid, fsn, sem))
        ct_count += 1
    log(f'  concept_terms: {ct_count:,} rows inserted')

    # Create indexes
    cur.execute('CREATE INDEX idx_terms_snomed ON terms (snomed_concept_id)')
    cur.execute('CREATE INDEX idx_terms_sapdt  ON terms (sapdt_concept_id)')
    cur.execute('CREATE INDEX idx_terms_display ON terms (display_name)')
    cur.execute('CREATE INDEX idx_rel_src ON relationships (source_id)')
    cur.execute('CREATE INDEX idx_rel_dst ON relationships (destination_id)')
    cur.execute('CREATE INDEX idx_ku_cid ON ku_synonym_text (concept_id)')

    # FTS virtual table for fast text search
    try:
        cur.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS terms_fts USING fts5(
            display_name, synonym, snomed_fsn, sapdt_fsn,
            content="terms", content_rowid="id"
        )''')
        cur.execute('INSERT INTO terms_fts(terms_fts) VALUES("rebuild")')
        log('  FTS index built')
    except Exception as e:
        log(f'  FTS skipped: {e}', 'WARN')

    conn.commit()
    conn.close()

    # --- Atomic replace: swap temp → final ---
    if os.path.exists(DB_OUT):
        os.replace(DB_TEMP, DB_OUT)
    else:
        os.rename(DB_TEMP, DB_OUT)

    # --- Auto Compress to .gz ---
    gz_out = DB_OUT + '.gz'
    log(f'Compressing database to {os.path.basename(gz_out)}...')
    import gzip, shutil
    with open(DB_OUT, 'rb') as f_in:
        with gzip.open(gz_out, 'wb', compresslevel=9) as f_out:
            shutil.copyfileobj(f_in, f_out)
    gz_size = os.path.getsize(gz_out) / (1024 * 1024)

    elapsed = time.time() - t0
    log('')
    log('=' * 60)
    log(f'✅ Build complete in {elapsed:.1f}s')
    log(f'   Output: {DB_OUT}')
    log(f'   Compressed: {gz_out} ({gz_size:.1f} MB)')
    log(f'   terms: {rows_inserted:,} | relationships: {rel_count:,} | concept_terms: {ct_count:,}')
    log('=' * 60)


if __name__ == '__main__':
    build()
