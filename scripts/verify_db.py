#!/usr/bin/env python3
"""
verify_db.py (v6.0)
===================
ชุดตรวจสอบความถูกต้องของฐานข้อมูล terminology_search.db แบบอัตโนมัติ (Automated QA & Integrity Audit)
ตรวจสอบครบ 5 มิติ:
  1. โครงสร้างตารางและ SQLite Physical Integrity (Schema 32 คอลัมน์, 4 ตารางหลัก, FTS5, Indexes)
  2. ความครบถ้วนของจำนวนข้อมูลเทียบกับต้นฉบับ (Completeness & Exact Counts)
  3. ความสมบูรณ์ของฟิลด์บังคับ (Zero Empty/Broken Critical Fields)
  4. ความถูกต้องของกฎการคัดเลือกชื่อ (Display Name & FSN Priority Rules)
  5. การทำงานจริงของระบบค้นหา (FTS5 + KU Thai Synonyms) และโครงสร้างลำดับชั้น (Parents / Children / Replacements)
"""

import os
import sys
import sqlite3

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR    = os.path.dirname(SCRIPT_DIR)
DB_PATH    = os.path.join(APP_DIR, 'terminology_search.db')

EXPECTED_COLUMNS = [
    'id', 'display_name', 'in_sapdt', 'in_vsct', 'in_sct_inter',
    'sapdt_concept_id', 'sapdt_status', 'sapdt_change_type', 'sapdt_description_id',
    'sapdt_fsn', 'sapdt_preferred', 'sapdt_acceptable', 'synonym', 'sapdt_semantic_type',
    'snomed_concept_id', 'snomed_fsn', 'snomed_preferred_term', 'snomed_all_synonyms',
    'snomed_active', 'snomed_module', 'snomed_semantic_type', 'body_system',
    'snomed_definition_status', 'snomed_parent_concepts', 'match_type',
    'concept_count', 'all_snomed_concept_ids', 'replacement_concept_id', 'match_confidence',
    'updated_at', 'updated_by', 'created_at'
]


def run_audit():
    print('=' * 74)
    print('🔍 รายงานการตรวจสอบความถูกต้องฐานข้อมูล KAHIS Terminology DB (QA Audit v6.0)')
    print('=' * 74)

    if not os.path.exists(DB_PATH):
        print(f'❌ ไม่พบไฟล์ฐานข้อมูล: {DB_PATH}')
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    passed = 0
    failed = 0

    def check(title, condition, detail=''):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f'  ✅ [PASS] {title}' + (f' -> {detail}' if detail else ''))
        else:
            failed += 1
            print(f'  ❌ [FAIL] {title}' + (f' -> {detail}' if detail else ''))

    # ------------------------------------------------------------------
    # มิติที่ 1: โครงสร้างตารางและ SQLite Integrity
    # ------------------------------------------------------------------
    print('\n[มิติที่ 1] ตรวจสอบโครงสร้างตารางและไฟล์ฐานข้อมูล (Schema & Integrity)')
    integ = cur.execute('PRAGMA integrity_check').fetchone()[0]
    check('SQLite PRAGMA integrity_check', integ == 'ok', integ)

    tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table','virtual table')").fetchall()}
    for tname in ('terms', 'relationships', 'concept_terms', 'ku_synonym_text', 'terms_fts'):
        check(f'มีตาราง {tname}', tname in tables)

    cols = [r[1] for r in cur.execute('PRAGMA table_info(terms)').fetchall()]
    check('ตาราง terms มีครบ 32 คอลัมน์ และเรียงลำดับตรงกับระบบเดิม 100%', cols == EXPECTED_COLUMNS, f'{len(cols)} คอลัมน์')

    indexes = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
    expected_idx = {
        'idx_terms_snomed', 'idx_terms_sapdt', 'idx_terms_display',
        'idx_terms_sem', 'idx_terms_body', 'idx_rel_src', 'idx_rel_dst', 'idx_ku_cid'
    }
    check('มี Indexes ครบทั้ง 8 ตัว', expected_idx.issubset(indexes), f'พบ {len(expected_idx & indexes)}/8')

    # ------------------------------------------------------------------
    # มิติที่ 2: ความครบถ้วนของจำนวนข้อมูลเทียบกับไฟล์ต้นฉบับ
    # ------------------------------------------------------------------
    print('\n[มิติที่ 2] ตรวจสอบความครบถ้วนของจำนวนข้อมูลเทียบกับต้นฉบับ (Completeness)')
    total_terms = cur.execute('SELECT COUNT(*) FROM terms').fetchone()[0]
    check('จำนวน Concepts สัตวแพทย์ทั้งหมด (SA-PDT ∪ VSCT)', total_terms >= 42299, f'{total_terms:,} แถว (เป้าหมาย >= 42,299)')

    dup_snomed = cur.execute("SELECT COUNT(*) FROM (SELECT snomed_concept_id FROM terms WHERE snomed_concept_id != '' GROUP BY snomed_concept_id HAVING COUNT(*) > 1)").fetchone()[0]
    check('ไม่มีรหัส snomed_concept_id ซ้ำซ้อนในตาราง terms', dup_snomed == 0, f'ซ้ำ {dup_snomed} รหัส')

    sapdt_total = cur.execute("SELECT COUNT(*) FROM terms WHERE in_sapdt='Yes'").fetchone()[0]
    sapdt_act   = cur.execute("SELECT COUNT(*) FROM terms WHERE in_sapdt='Yes' AND sapdt_status='Active'").fetchone()[0]
    sapdt_ret   = cur.execute("SELECT COUNT(*) FROM terms WHERE in_sapdt='Yes' AND sapdt_status='Retired'").fetchone()[0]
    check('จำนวน SA-PDT ครบถ้วนตรงตามต้นฉบับ', sapdt_total == 4489 and sapdt_act == 4103 and sapdt_ret == 386,
          f'รวม {sapdt_total:,} (Active={sapdt_act:,}, Retired={sapdt_ret:,})')

    vsct_total = cur.execute("SELECT COUNT(*) FROM terms WHERE in_vsct='Yes'").fetchone()[0]
    check('จำนวน VSCT (Concept 37,416 ∪ Description 40,829) ครบถ้วน', vsct_total == 40830, f'{vsct_total:,} แถว')

    vsct_desc_only = cur.execute("SELECT COUNT(*) FROM terms WHERE in_vsct='Yes' AND in_sct_inter='Yes'").fetchone()[0]
    check('มีกลุ่ม Concept ที่เชื่อมกับ SCT-Int (VSCT ∩ SCT-Int = 3,074 + VSCT Desc = 3,414)', vsct_desc_only == 6488, f'{vsct_desc_only:,} แถว')

    rel_count = cur.execute('SELECT COUNT(*) FROM relationships').fetchone()[0]
    check('จำนวนความสัมพันธ์ในตาราง relationships', rel_count > 1300000, f'{rel_count:,} แถว')

    ct_count = cur.execute('SELECT COUNT(*) FROM concept_terms').fetchone()[0]
    check('จำนวนชื่อ FSN ทั้งโลกในตาราง concept_terms', ct_count > 550000, f'{ct_count:,} แถว')

    ku_count = cur.execute('SELECT COUNT(*) FROM ku_synonym_text').fetchone()[0]
    check('จำนวนคำพ้องภาษาไทยในตาราง ku_synonym_text', ku_count >= 190, f'{ku_count:,} แถว')

    # ------------------------------------------------------------------
    # มิติที่ 3: ความสมบูรณ์ของฟิลด์บังคับ (Zero Missing Critical Fields)
    # ------------------------------------------------------------------
    print('\n[มิติที่ 3] ตรวจสอบความสมบูรณ์ของฟิลด์บังคับ (Data Quality & Zero Nulls)')
    empty_disp = cur.execute("SELECT COUNT(*) FROM terms WHERE display_name IS NULL OR trim(display_name)=''").fetchone()[0]
    check('ไม่มีแถวที่ display_name ว่างเปล่า', empty_disp == 0, f'ว่างเปล่า {empty_disp} แถว')

    numeric_disp = cur.execute("SELECT COUNT(*) FROM terms WHERE display_name GLOB '[0-9]*' AND display_name = snomed_concept_id").fetchone()[0]
    check('ไม่มีแถวที่ display_name หลุดเป็นรหัสตัวเลข Concept ID', numeric_disp == 0, f'หลุดเป็นตัวเลข {numeric_disp} แถว')

    empty_fsn = cur.execute("SELECT COUNT(*) FROM terms WHERE snomed_fsn IS NULL OR trim(snomed_fsn)=''").fetchone()[0]
    check('ไม่มีแถวที่ snomed_fsn ว่างเปล่า', empty_fsn == 0, f'ว่างเปล่า {empty_fsn} แถว')

    empty_sem = cur.execute("SELECT COUNT(*) FROM terms WHERE snomed_semantic_type IS NULL OR trim(snomed_semantic_type)=''").fetchone()[0]
    check('ไม่มีแถวที่ snomed_semantic_type ว่างเปล่า', empty_sem == 0, f'ว่างเปล่า {empty_sem} แถว')

    empty_body = cur.execute("SELECT COUNT(*) FROM terms WHERE body_system IS NULL OR trim(body_system)=''").fetchone()[0]
    check('ไม่มีแถวที่ body_system (Categories) ว่างเปล่า', empty_body == 0, f'ว่างเปล่า {empty_body} แถว')

    has_parents = cur.execute("SELECT COUNT(*) FROM terms WHERE snomed_parent_concepts != ''").fetchone()[0]
    check('คำนวณ snomed_parent_concepts สำหรับ Active Concepts ครบถ้วน', has_parents >= 40400, f'มีรหัสแม่ {has_parents:,} แถว')

    has_repl = cur.execute("SELECT COUNT(*) FROM terms WHERE replacement_concept_id != ''").fetchone()[0]
    check('ดึงรหัสทดแทน replacement_concept_id สำหรับรหัสที่ยกเลิก', has_repl >= 1700, f'พบ {has_repl:,} รหัสที่มีรหัสทดแทน')

    # ------------------------------------------------------------------
    # มิติที่ 4: ความถูกต้องของกฎการคัดเลือกชื่อ (Priority Rules & Benchmark Cases)
    # ------------------------------------------------------------------
    print('\n[มิติที่ 4] ตรวจสอบกฎการคัดเลือกชื่อ (Display Name & FSN Priority Rules)')
    sapdt_mismatch = cur.execute("SELECT COUNT(*) FROM terms WHERE in_sapdt='Yes' AND display_name != sapdt_preferred").fetchone()[0]
    check('กฎลำดับที่ 1: รหัสที่อยู่ใน SA-PDT ใช้ชื่อ sapdt_preferred เป็น display_name 100%', sapdt_mismatch == 0,
          f'ตรงกัน {sapdt_total - sapdt_mismatch:,}/{sapdt_total:,}')

    benchmarks = [
        ('95570007',  'Renal calculi',  'Kidney stone (disorder)',          'Urinary system',   'Nephrolithiasis'),
        ('235919008', 'Gallstones',     'Gallbladder calculus (disorder)',  'Digestive system', 'Cholecystolithiasis'),
        ('70650003',  'Bladder stone',  'Urinary bladder stone (disorder)', 'Urinary system',   'Vesical calculus'),
        ('297288000', 'Liver calculus', 'Liver calculus (disorder)',        'Digestive system', 'Hepatolithiasis'),
    ]
    for cid, exp_disp, exp_fsn, exp_body, exp_syn in benchmarks:
        row = cur.execute('SELECT * FROM terms WHERE snomed_concept_id=?', (cid,)).fetchone()
        ok = (
            row is not None and
            row['display_name'] == exp_disp and
            row['snomed_fsn'] == exp_fsn and
            row['body_system'] == exp_body and
            exp_syn.lower() in row['synonym'].lower()
        )
        detail = f"display='{row['display_name']}', fsn='{row['snomed_fsn']}', body='{row['body_system']}', syn มี '{exp_syn}'" if row else 'ไม่พบรหัส'
        check(f'ตรวจสอบ Concept ตัวแทน {cid}', ok, detail)

    # ------------------------------------------------------------------
    # มิติที่ 5: ทดสอบการค้นหาจริง (FTS5 + KU Thai) และการดึง Parents/Children
    # ------------------------------------------------------------------
    print('\n[มิติที่ 5] ทดสอบการค้นหา (FTS5 & Thai Synonyms) และการดึง Parents/Children')
    fts_cases = [
        ('Nephrolithiasis*', '95570007'),
        ('Cholecystolithiasis*', '235919008'),
        ('Hepatolithiasis*', '297288000'),
    ]
    for q_fts, exp_cid in fts_cases:
        hits = [r[0] for r in cur.execute(
            'SELECT snomed_concept_id FROM terms WHERE id IN (SELECT rowid FROM terms_fts WHERE terms_fts MATCH ?)',
            (q_fts,)
        ).fetchall()]
        check(f'ค้นหา FTS5 คำพ้อง "{q_fts}" เจอรหัส {exp_cid}', exp_cid in hits, f'พบ {len(hits)} รายการ')

    thai_hits = [r[0] for r in cur.execute(
        "SELECT concept_id FROM ku_synonym_text WHERE ku_synonym_text LIKE '%นิ่วในไต%'"
    ).fetchall()]
    check('ค้นหาคำพ้องภาษาไทย "นิ่วในไต" ใน ku_synonym_text เจอรหัส 95570007', '95570007' in thai_hits, f'พบ {thai_hits}')

    # ทดสอบดึง Parents และ Children ของ 95570007 (Renal calculi)
    parents_95570007 = cur.execute('''
        SELECT r.destination_id, c.term
        FROM relationships r
        LEFT JOIN concept_terms c ON c.concept_id = r.destination_id
        WHERE r.source_id = '95570007' AND r.type_id = '116680003'
    ''').fetchall()
    children_95570007 = cur.execute('''
        SELECT r.source_id, c.term
        FROM relationships r
        LEFT JOIN concept_terms c ON c.concept_id = r.source_id
        WHERE r.destination_id = '95570007' AND r.type_id = '116680003'
    ''').fetchall()
    check('ดึง Parents (Is a) ของ 95570007 พร้อมชื่อ FSN ได้ครบถ้วน',
          len(parents_95570007) > 0 and all(r['term'] for r in parents_95570007),
          f'พบ Parents {len(parents_95570007)} รายการ')
    check('ดึง Children (Is a) ของ 95570007 พร้อมชื่อ FSN ได้ครบถ้วน',
          len(children_95570007) > 0 and all(r['term'] for r in children_95570007),
          f'พบ Children {len(children_95570007)} รายการ')

    conn.close()

    print('\n' + '=' * 74)
    if failed == 0:
        print(f'🎉 สรุปผลการตรวจสอบ: ผ่านทั้งหมด {passed}/{passed} รายการ (ไม่พบข้อผิดพลาดแม้แต่รายการเดียว)')
    else:
        print(f'⚠️ สรุปผลการตรวจสอบ: ผ่าน {passed} รายการ | ไม่ผ่าน {failed} รายการ')
    print('=' * 74)
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    run_audit()
