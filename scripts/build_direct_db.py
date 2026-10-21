#!/usr/bin/env python3
"""
build_direct_db.py (v6.0)
=========================
สร้างและอัปเดตฐานข้อมูล terminology_search.db โดยตรงจาก 3 แหล่งข้อมูลต้นฉบับ + KU Custom Data:
  1. SA-PDT Release File (SA-PDTReleaseFile_full_*.txt)
  2. SNOMED CT Veterinary Extension (SnomedCT_VETExtension_* — Folder หรือ .zip)
  3. SNOMED CT International Edition (SnomedCT_InternationalRF2_* — Folder หรือ .zip)
  4. KU Custom Data (ku_custom_synonyms.csv + ตาราง ku_synonym_text และ Custom Concepts ใน DB เดิม)

คุณสมบัติหลัก (v6.0 Specification):
  - คงโครงสร้างตาราง (Schema 4 ตาราง, terms 32 คอลัมน์) เดิม 100% (Zero Breaking Changes)
  - บรรจุครบทั้ง 42,299 Concepts (SA-PDT 4,489 ∪ VSCT Concept 37,416 ∪ VSCT Description 3,414)
  - คัดเลือก display_name ตามลำดับ: SA-PDT Preferred > VSCT Preferred (332501000009101) > SCT-Int Preferred (900000000000509007)
  - คัดเลือก snomed_fsn ตามลำดับ: VSCT FSN > SCT-Int FSN
  - รวมคำพ้องภาษาอังกฤษทุกแหล่ง (SA-PDT ∪ VSCT -en ∪ SCT-Int -en) ลงในคอลัมน์ synonym และ FTS5
  - คำนวณ body_system (Categories) และ snomed_parent_concepts ครบทุกแถวในขั้นตอนเดียว
  - Update-Safe 100%: สำรอง DB เดิม, รักษา ku_synonym_text และ Custom Concepts (match_type='ku_custom'),
    ดึงรหัสทดแทน replacement_concept_id จาก Association Refset และป้องกันรหัสกำพร้า (Zero Orphans)
"""

import os
import sys
import glob
import csv
import re
import io
import gzip
import shutil
import zipfile
import sqlite3
import time

# รองรับการแสดงผลภาษาไทยบน Windows Console / Subprocess
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# รองรับฟิลด์ขนาดใหญ่ในไฟล์ RF2
csv.field_size_limit(min(sys.maxsize, 10 * 1024 * 1024))

# ---------------------------------------------------------------------------
# Path Resolution
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR    = os.path.dirname(SCRIPT_DIR)               # .../kahis-terminology/
KAHIS_DIR  = os.path.dirname(APP_DIR)                  # .../GitHub/
DB_OUT     = os.path.join(APP_DIR, 'terminology_search.db')
DB_TEMP    = DB_OUT + '.building'

# SNOMED CT Constants
IS_A_TYPE       = '116680003'
FINDING_SITE    = '363698007'
PROC_SITES      = ('363704007', '405813007', '405814008')
FSN_TYPE        = '900000000000003001'
SYN_TYPE        = '900000000000013009'
PREF_ACCEPT     = '900000000000548007'
VTSL_LANG_REF   = '332501000009101'
US_LANG_REF     = '900000000000509007'
PRIMITIVE       = '900000000000074008'
FULLY_DEF       = '900000000000073002'
ASSOC_REFSETS   = {
    '900000000000526001',  # REPLACED BY
    '900000000000527005',  # SAME AS
    '900000000000523009',  # POSSIBLY EQUIVALENT TO
    '900000000000528000',  # WAS A
}

REL_TYPE_NAMES = {
    '116680003': 'Is a',
    '363698007': 'Finding site',
    '363704007': 'Procedure site',
    '405813007': 'Procedure site - Direct',
    '405814008': 'Procedure site - Indirect',
    '116676008': 'Associated morphology',
    '272741003': 'Laterality',
    '246075003': 'Causative agent',
    '363700003': 'Direct morphology',
    '363699004': 'Direct device',
    '260686004': 'Method',
    '363714003': 'Interprets',
    '370135005': 'Pathological process',
    '246454002': 'Occurrence',
    '263502005': 'Clinical course',
}

BODY_SYSTEM_MAP = {
    '272625008': 'Digestive system',
    '278887002': 'Digestive system',
    '86762007':  'Digestive system',
    '20139000':  'Respiratory system',
    '113257007': 'Cardiovascular system',
    '119235005': 'Nervous system',
    '25087005':  'Nervous system',
    '26107004':  'Musculoskeletal system',
    '362965005': 'Reproductive system',
    '278891008': 'Reproductive system',
    '122489005': 'Urinary system',
    '118671006': 'Endocrine system',
    '244184003': 'Integumentary system (Skin)',
    '48075008':  'Integumentary system (Skin)',
    '181750001': 'Immune system',
    '278896008': 'Lymphatic system',
    '361077002': 'Visual system (Eye)',
    '81745001':  'Visual system (Eye)',
    '361078007': 'Auditory system (Ear)',
    '117590005': 'Auditory system (Ear)',
    '362874006': 'Hematopoietic system (Blood)',
    '278198002': 'Systemic / Body as a whole',
    '127954009': 'Head and neck structure',
}

DRY_RUN = '--dry-run' in sys.argv


def log(msg, tag='INFO'):
    print(f'[{tag}] {msg}', flush=True)


def strip_fsn_tag(fsn_text):
    """ตัดวงเล็บ semantic tag ท้ายชื่อ FSN ออก เช่น 'Kidney stone (disorder)' -> 'Kidney stone'"""
    if not fsn_text:
        return ''
    return re.sub(r'\s*\([^)]+\)\s*$', '', fsn_text).strip()


def extract_sem_tag(fsn_text):
    """ดึงคำในวงเล็บท้ายสุดของ FSN เช่น 'Kidney stone (disorder)' -> 'disorder'"""
    if not fsn_text:
        return ''
    m = re.search(r'\(([^)]+)\)\s*$', fsn_text)
    return m.group(1).strip() if m else ''


# ---------------------------------------------------------------------------
# RF2 Reader Helper (รองรับทั้งโฟลเดอร์ที่แตกแล้ว และไฟล์ .zip โดยไม่ต้องแตกไฟล์)
# ---------------------------------------------------------------------------
class RF2Archive:
    def __init__(self, path):
        self.path = path
        self.is_zip = zipfile.is_zipfile(path) if os.path.isfile(path) else False
        self.zf = zipfile.ZipFile(path, 'r') if self.is_zip else None

    def find_member(self, subfolder_hint, prefix_pattern, lang_en_only=False):
        """ค้นหาไฟล์ใน Snapshot/ ตาม prefix_pattern"""
        if self.is_zip:
            candidates = []
            for name in self.zf.namelist():
                if 'Snapshot/' not in name or not name.endswith('.txt'):
                    continue
                base = os.path.basename(name)
                if not base.startswith(prefix_pattern):
                    continue
                if lang_en_only and ('-es_' in base or '-it_' in base):
                    continue
                if lang_en_only and '-en_' in base:
                    candidates.insert(0, name)
                else:
                    candidates.append(name)
            return candidates[0] if candidates else None
        else:
            pattern = os.path.join(self.path, '**', 'Snapshot', '**', f'{prefix_pattern}*.txt')
            hits = glob.glob(pattern, recursive=True)
            if not hits:
                pattern2 = os.path.join(self.path, '**', f'{prefix_pattern}*.txt')
                hits = [h for h in glob.glob(pattern2, recursive=True) if 'Snapshot' in h]
            if lang_en_only:
                en_hits = [h for h in hits if '-en_' in os.path.basename(h)]
                if en_hits:
                    return sorted(en_hits)[-1]
                hits = [h for h in hits if '-es_' not in os.path.basename(h) and '-it_' not in os.path.basename(h)]
            return sorted(hits)[-1] if hits else None

    def open_tsv_lines(self, member):
        """คืนค่า iterator ของบรรทัดข้อความ (UTF-8-SIG)"""
        if self.is_zip:
            raw = self.zf.open(member, 'r')
            return io.TextIOWrapper(raw, encoding='utf-8-sig', errors='replace')
        else:
            return open(member, 'r', encoding='utf-8-sig', errors='replace')

    def close(self):
        if self.zf:
            self.zf.close()


# ---------------------------------------------------------------------------
# Auto-detect Source Folders / Zip Archives
# ---------------------------------------------------------------------------
def get_search_roots():
    roots = [
        APP_DIR,
        KAHIS_DIR,
        os.path.dirname(KAHIS_DIR),
        os.path.expanduser('~/Downloads'),
    ]
    # เพิ่มตัวแปรสภาพแวดล้อมถ้ามีการระบุ
    env_dir = os.environ.get('KAHIS_SOURCES_DIR')
    if env_dir and os.path.exists(env_dir):
        roots.insert(0, env_dir)
    return [r for r in roots if r and os.path.exists(r)]


def find_sources():
    roots = get_search_roots()
    sapdt_file = None
    vsct_src   = None
    sct_src    = None

    # 1. ค้นหาไฟล์ SA-PDTReleaseFile_full_*.txt
    sapdt_candidates = []
    for r in roots:
        for pat in [
            os.path.join(r, 'SA-PDT*', '**', 'SA-PDTReleaseFile_full_*.txt'),
            os.path.join(r, 'SA-PDT*', 'SA-PDTReleaseFile_full_*.txt'),
            os.path.join(r, 'Small Animal Problem*', '**', 'SA-PDTReleaseFile_full_*.txt'),
        ]:
            sapdt_candidates.extend(glob.glob(pat, recursive=True))
    if sapdt_candidates:
        sapdt_file = sorted(sapdt_candidates, key=lambda p: os.path.basename(p))[-1]

    def has_refset(path):
        if os.path.isdir(path):
            return bool(glob.glob(os.path.join(path, '**', 'der2_cRefset_LanguageSnapshot*.txt'), recursive=True))
        if path.endswith('.zip') and zipfile.is_zipfile(path):
            try:
                with zipfile.ZipFile(path, 'r') as zf:
                    return any('der2_cRefset_LanguageSnapshot' in n for n in zf.namelist())
            except Exception:
                return False
        return False

    # 2. ค้นหา VSCT (โฟลเดอร์ หรือ .zip)
    vsct_candidates = []
    for r in roots:
        for pat in [
            os.path.join(r, 'SnomedCT_VETExtension_*'),
            os.path.join(r, 'Small Animal Problem*', 'SnomedCT_VETExtension_*'),
        ]:
            for hit in glob.glob(pat):
                if os.path.isdir(hit) or hit.endswith('.zip'):
                    vsct_candidates.append(hit)
    if vsct_candidates:
        # ให้ความสำคัญกับชุดที่มีไฟล์ Refset ครบถ้วน และโฟลเดอร์ที่แตกแล้วก่อน
        vsct_candidates.sort(key=lambda p: (has_refset(p), os.path.basename(p).replace('.zip', ''), os.path.isdir(p)))
        vsct_src = vsct_candidates[-1]

    # 3. ค้นหา SCT International (โฟลเดอร์ หรือ .zip)
    sct_candidates = []
    for r in roots:
        for hit in glob.glob(os.path.join(r, 'SnomedCT_InternationalRF2_*')):
            if os.path.isdir(hit) or hit.endswith('.zip'):
                sct_candidates.append(hit)
    if sct_candidates:
        sct_candidates.sort(key=lambda p: (has_refset(p), os.path.basename(p).replace('.zip', ''), os.path.isdir(p)))
        sct_src = sct_candidates[-1]

    return sapdt_file, vsct_src, sct_src


# ---------------------------------------------------------------------------
# Step 0: Backup & Extract Existing Custom Data (Update-Safe Pipeline)
# ---------------------------------------------------------------------------
def backup_and_extract_existing():
    """
    สำรองไฟล์ DB เดิมเข้าโฟลเดอร์ backup/ และดึงข้อมูล:
      1. ku_synonym_text จาก DB เดิม + ไฟล์ ku_custom_synonyms.csv
      2. แถวในตาราง terms ของ DB เดิม (ทั้ง match_type='ku_custom' และรหัสเดิมเพื่อป้องกัน Orphan)
    """
    ku_synonyms_map = {}  # (concept_id, text_lower) -> (concept_id, text, lang_tag, created_at)
    old_terms_map   = {}  # cid -> dict of row columns
    custom_rows     = []  # list of dicts for match_type == 'ku_custom'

    # 0.1 อ่านจากไฟล์ ku_custom_synonyms.csv ในโปรเจกต์
    csv_paths = [
        os.path.join(APP_DIR, 'ku_custom_synonyms.csv'),
        os.path.join(APP_DIR, 'Custom_data', 'ku_custom_synonyms.csv'),
        os.path.join(APP_DIR, 'output', 'ku_custom_synonyms.csv'),
    ]
    for cpath in csv_paths:
        if os.path.exists(cpath):
            try:
                with open(cpath, 'r', encoding='utf-8-sig') as f:
                    for row in csv.DictReader(f):
                        cid  = (row.get('concept_id') or row.get('Concept Identifier') or '').strip()
                        text = (row.get('ku_synonym_text') or row.get('synonym_text') or row.get('Synonym') or '').strip()
                        lang = (row.get('lang_tag') or 'ku').strip()
                        cat  = (row.get('created_at') or time.strftime('%Y-%m-%d %H:%M:%S')).strip()
                        if cid and text:
                            key = (cid, text.lower())
                            if key not in ku_synonyms_map:
                                ku_synonyms_map[key] = (cid, text, lang, cat)
            except Exception as e:
                log(f'ไม่สามารถอ่านไฟล์ {cpath}: {e}', 'WARN')

    # 0.2 หากมี DB เดิมอยู่แล้ว ให้สำรองและดึงข้อมูลเดิมออกมา
    if os.path.exists(DB_OUT):
        backup_dir = os.path.join(APP_DIR, 'backup')
        os.makedirs(backup_dir, exist_ok=True)
        ts = time.strftime('%Y%m%d_%H%M%S')
        bkp_db = os.path.join(backup_dir, f'terminology_search_{ts}.db')
        try:
            shutil.copy2(DB_OUT, bkp_db)
            log(f'สำรองฐานข้อมูลเดิมไว้ที่: backup/{os.path.basename(bkp_db)}')
        except Exception as e:
            log(f'สำรองฐานข้อมูลเดิมไม่สำเร็จ: {e}', 'WARN')

        try:
            conn = sqlite3.connect(DB_OUT)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # ดึงข้อมูลจาก ku_synonym_text
            try:
                cur.execute('SELECT concept_id, ku_synonym_text, lang_tag, created_at FROM ku_synonym_text')
                for r in cur.fetchall():
                    cid  = (r['concept_id'] or '').strip()
                    text = (r['ku_synonym_text'] or '').strip()
                    lang = (r['lang_tag'] or 'ku').strip()
                    cat  = (r['created_at'] or time.strftime('%Y-%m-%d %H:%M:%S')).strip()
                    if cid and text:
                        key = (cid, text.lower())
                        if key not in ku_synonyms_map:
                            ku_synonyms_map[key] = (cid, text, lang, cat)
            except Exception:
                pass

            # ดึงข้อมูลจาก terms เดิม
            try:
                cur.execute('SELECT * FROM terms')
                for r in cur.fetchall():
                    d = dict(r)
                    mtype = (d.get('match_type') or '').strip()
                    if mtype == 'ku_custom':
                        custom_rows.append(d)
                    else:
                        cid = (d.get('snomed_concept_id') or d.get('sapdt_concept_id') or '').strip()
                        if cid:
                            old_terms_map[cid] = d
            except Exception:
                pass

            conn.close()
        except Exception as e:
            log(f'อ่านข้อมูลจาก DB เดิมไม่สำเร็จ: {e}', 'WARN')

    log(f'รวบรวมคำพ้อง ku ได้ทั้งหมด: {len(ku_synonyms_map):,} รายการ | Custom Concepts: {len(custom_rows):,} รายการ')
    return ku_synonyms_map, old_terms_map, custom_rows


# ---------------------------------------------------------------------------
# Step 1: Read SA-PDT Release File
# ---------------------------------------------------------------------------
def read_sapdt_file(sapdt_file):
    """
    อ่านไฟล์ SA-PDTReleaseFile_full_*.txt
    Columns: Status | Concept Identifier | Description Identifier | Description Term | Term Designation
    """
    log(f'  กำลังอ่าน SA-PDT: {os.path.basename(sapdt_file)}')
    agg = {}
    with open(sapdt_file, 'r', encoding='utf-8-sig', errors='replace') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            cid = (row.get('Concept Identifier') or '').strip()
            if not cid:
                continue
            status  = (row.get('Status') or 'Active').strip()
            term    = (row.get('Description Term') or '').strip()
            desig   = (row.get('Term Designation') or 'Acceptable').strip()
            desc_id = (row.get('Description Identifier') or '').strip()

            if cid not in agg:
                agg[cid] = {
                    'status': 'Retired',
                    'preferred': '',
                    'preferred_active': False,
                    'synonyms': [],
                    'desc_ids': [],
                }

            rec = agg[cid]
            if status == 'Active':
                rec['status'] = 'Active'

            if desc_id and desc_id not in rec['desc_ids']:
                rec['desc_ids'].append(desc_id)

            if desig == 'Preferred':
                # ให้คำที่เป็น Active ชนะคำที่เป็น Retired เสมอ
                if status == 'Active' or not rec['preferred']:
                    rec['preferred'] = term
                    if status == 'Active':
                        rec['preferred_active'] = True
            else:
                if term and term not in rec['synonyms']:
                    rec['synonyms'].append(term)

    # กรณีในไฟล์ SA-PDT มีเฉพาะแถว Acceptable และไม่มีแถว Preferred (พบ 2 รหัสในต้นฉบับ) ให้ใช้คำแรกของ Acceptable แทน
    for cid, rec in agg.items():
        if not rec['preferred'] and rec['synonyms']:
            rec['preferred'] = rec['synonyms'][0]

    log(f'  SA-PDT โหลดสำเร็จ: {len(agg):,} Concepts')
    return agg


# ---------------------------------------------------------------------------
# Step 2: Read VSCT (5 Snapshot Files)
# ---------------------------------------------------------------------------
def read_vsct_archive(vsct_path):
    arc = RF2Archive(vsct_path)

    conc_member  = arc.find_member('Terminology', 'sct2_Concept_Snapshot')
    desc_member  = arc.find_member('Terminology', 'sct2_Description_Snapshot', lang_en_only=True)
    rel_member   = arc.find_member('Terminology', 'sct2_Relationship_Snapshot')
    lang_member  = arc.find_member('Language', 'der2_cRefset_LanguageSnapshot', lang_en_only=True)
    assoc_member = arc.find_member('Content', 'der2_cRefset_AssociationSnapshot')

    if not all([conc_member, desc_member, rel_member]):
        arc.close()
        raise RuntimeError(f'ไฟล์ VSCT ไม่ครบถ้วนใน {vsct_path}')

    # 2.1 Language Refset (VTSL 332501000009101 & US 900000000000509007)
    vtsl_pref_dids = set()
    us_pref_dids   = set()
    if lang_member:
        log(f'  กำลังอ่าน VSCT Language Refset: {os.path.basename(lang_member)}')
        with arc.open_tsv_lines(lang_member) as f:
            f.readline()  # skip header
            for line in f:
                parts = line.rstrip('\r\n').split('\t')
                if len(parts) > 6 and parts[2] == '1' and parts[6] == PREF_ACCEPT:
                    refset_id = parts[4]
                    did       = parts[5]
                    if refset_id == VTSL_LANG_REF:
                        vtsl_pref_dids.add(did)
                    elif refset_id == US_LANG_REF:
                        us_pref_dids.add(did)
        log(f'  VSCT Preferred Description IDs: VTSL={len(vtsl_pref_dids):,}, US={len(us_pref_dids):,}')

    # 2.2 Concept Snapshot
    vsct_concs = {}
    log(f'  กำลังอ่าน VSCT Concepts: {os.path.basename(conc_member)}')
    with arc.open_tsv_lines(conc_member) as f:
        f.readline()
        for line in f:
            parts = line.rstrip('\r\n').split('\t')
            if len(parts) >= 5:
                cid = parts[0]
                if cid:
                    vsct_concs[cid] = {
                        'active': parts[2],
                        'module': parts[3],
                        'definition_status': parts[4],
                    }
    log(f'  VSCT Concepts: {len(vsct_concs):,}')

    # 2.3 Description Snapshot (-en)
    vsct_descs = {}
    log(f'  กำลังอ่าน VSCT Descriptions (-en): {os.path.basename(desc_member)}')
    with arc.open_tsv_lines(desc_member) as f:
        f.readline()
        for line in f:
            parts = line.rstrip('\r\n').split('\t')
            if len(parts) >= 8:
                did    = parts[0]
                active = parts[2]
                mid    = parts[3]
                cid    = parts[4]
                dtype  = parts[6]
                term   = parts[7]
                if not cid or not term:
                    continue
                rec = vsct_descs.setdefault(cid, {
                    'fsn': '',
                    'inactive_fsn': '',
                    'vtsl_pref': '',
                    'us_pref': '',
                    'synonyms': [],
                    'inactive_syn': '',
                    'module': mid,
                })
                if active == '1':
                    if dtype == FSN_TYPE:
                        rec['fsn'] = term
                    elif dtype == SYN_TYPE:
                        if term not in rec['synonyms']:
                            rec['synonyms'].append(term)
                        if did in vtsl_pref_dids:
                            rec['vtsl_pref'] = term
                        elif did in us_pref_dids and not rec['us_pref']:
                            rec['us_pref'] = term
                else:
                    if dtype == FSN_TYPE and not rec['inactive_fsn']:
                        rec['inactive_fsn'] = term
                    elif dtype == SYN_TYPE and not rec['inactive_syn']:
                        rec['inactive_syn'] = term
    log(f'  VSCT Distinct Concept IDs in Descriptions: {len(vsct_descs):,}')

    # 2.4 Association Snapshot (Replacement Concept IDs)
    vsct_assoc = {}
    if assoc_member:
        log(f'  กำลังอ่าน VSCT Association Refset: {os.path.basename(assoc_member)}')
        with arc.open_tsv_lines(assoc_member) as f:
            f.readline()
            for line in f:
                parts = line.rstrip('\r\n').split('\t')
                if len(parts) >= 7 and parts[2] == '1' and parts[4] in ASSOC_REFSETS:
                    vsct_assoc[parts[5]] = parts[6]

    # 2.5 Relationship Snapshot
    vsct_rels    = []
    vet_parents  = {}
    vet_fs       = {}
    vet_ps       = {}
    log(f'  กำลังอ่าน VSCT Relationships: {os.path.basename(rel_member)}')
    with arc.open_tsv_lines(rel_member) as f:
        f.readline()
        for line in f:
            parts = line.rstrip('\r\n').split('\t')
            if len(parts) >= 8 and parts[2] == '1':
                src, dst, tid = parts[4], parts[5], parts[7]
                vsct_rels.append((src, dst, tid, 'VSCT'))
                if tid == IS_A_TYPE:
                    vet_parents.setdefault(src, set()).add(dst)
                elif tid == FINDING_SITE:
                    vet_fs.setdefault(src, set()).add(dst)
                elif tid in PROC_SITES:
                    vet_ps.setdefault(src, set()).add(dst)
    log(f'  VSCT Active Relationships: {len(vsct_rels):,}')

    arc.close()
    return vsct_concs, vsct_descs, vtsl_pref_dids, us_pref_dids, vsct_assoc, vsct_rels, vet_parents, vet_fs, vet_ps


# ---------------------------------------------------------------------------
# Step 3: Read SCT International (5 Snapshot Files, Optimized Streaming)
# ---------------------------------------------------------------------------
def read_sct_archive(sct_path, target_vet_cids, vtsl_pref_dids, vsct_us_pref_dids):
    arc = RF2Archive(sct_path)

    conc_member  = arc.find_member('Terminology', 'sct2_Concept_Snapshot')
    desc_member  = arc.find_member('Terminology', 'sct2_Description_Snapshot', lang_en_only=True)
    rel_member   = arc.find_member('Terminology', 'sct2_Relationship_Snapshot')
    lang_member  = arc.find_member('Language', 'der2_cRefset_LanguageSnapshot', lang_en_only=True)
    assoc_member = arc.find_member('Content', 'der2_cRefset_AssociationSnapshot')

    if not all([conc_member, desc_member, rel_member]):
        arc.close()
        raise RuntimeError(f'ไฟล์ SCT International ไม่ครบถ้วนใน {sct_path}')

    # 3.1 Concept Snapshot (เก็บเฉพาะรหัสใน target_vet_cids เพื่อประหยัด RAM)
    sct_concs = {}
    log(f'  กำลังอ่าน SCT-Int Concepts: {os.path.basename(conc_member)}')
    with arc.open_tsv_lines(conc_member) as f:
        f.readline()
        for line in f:
            parts = line.rstrip('\r\n').split('\t')
            if len(parts) >= 5:
                cid = parts[0]
                if cid in target_vet_cids:
                    sct_concs[cid] = {
                        'active': parts[2],
                        'module': parts[3],
                        'definition_status': parts[4],
                    }
    log(f'  SCT-Int Concepts (ที่ตรงกับฐานสัตวแพทย์): {len(sct_concs):,}')

    # 3.2 Description Snapshot (-en)
    # เก็บ FSN ของทุก Concept ลง sct_fsn_map (สำหรับ concept_terms + body_system)
    # และเก็บ Synonyms + Description IDs ของ target_vet_cids ลง sct_descs
    sct_fsn_map     = {}
    sct_descs       = {}
    target_desc_map = {}  # did -> (cid, term) เฉพาะของ target_vet_cids

    log(f'  กำลังอ่าน SCT-Int Descriptions (-en): {os.path.basename(desc_member)}')
    with arc.open_tsv_lines(desc_member) as f:
        f.readline()
        for line in f:
            parts = line.rstrip('\r\n').split('\t')
            if len(parts) >= 8:
                did    = parts[0]
                active = parts[2]
                mid    = parts[3]
                cid    = parts[4]
                dtype  = parts[6]
                term   = parts[7]
                if not cid or not term:
                    continue

                if dtype == FSN_TYPE:
                    if active == '1' or cid not in sct_fsn_map:
                        sct_fsn_map[cid] = term

                if cid in target_vet_cids:
                    rec = sct_descs.setdefault(cid, {
                        'fsn': '',
                        'inactive_fsn': '',
                        'vtsl_pref': '',
                        'us_pref': '',
                        'synonyms': [],
                        'inactive_syn': '',
                        'module': mid,
                    })
                    if active == '1':
                        if dtype == FSN_TYPE:
                            rec['fsn'] = term
                        elif dtype == SYN_TYPE:
                            if term not in rec['synonyms']:
                                rec['synonyms'].append(term)
                            # เช็คว่า Description ID นี้อยู่ใน VSCT Language Refset หรือไม่ (เช่น Bladder stone 117363016)
                            if did in vtsl_pref_dids:
                                rec['vtsl_pref'] = term
                            elif did in vsct_us_pref_dids and not rec['us_pref']:
                                rec['us_pref'] = term
                            else:
                                target_desc_map[did] = (cid, term)
                    else:
                        if dtype == FSN_TYPE and not rec['inactive_fsn']:
                            rec['inactive_fsn'] = term
                        elif dtype == SYN_TYPE and not rec['inactive_syn']:
                            rec['inactive_syn'] = term

    log(f'  SCT-Int Global FSNs: {len(sct_fsn_map):,} | Vet-Matched SCT Descs: {len(sct_descs):,}')

    # 3.3 Language Refset (US English 900000000000509007 สำหรับ target_desc_map)
    if lang_member and target_desc_map:
        log(f'  กำลังอ่าน SCT-Int Language Refset: {os.path.basename(lang_member)}')
        matched_prefs = 0
        with arc.open_tsv_lines(lang_member) as f:
            f.readline()
            for line in f:
                parts = line.rstrip('\r\n').split('\t')
                if len(parts) > 6 and parts[2] == '1' and parts[4] == US_LANG_REF and parts[6] == PREF_ACCEPT:
                    did = parts[5]
                    if did in target_desc_map:
                        cid, term = target_desc_map[did]
                        if not sct_descs[cid]['us_pref']:
                            sct_descs[cid]['us_pref'] = term
                            matched_prefs += 1
        log(f'  SCT-Int US Preferred Terms matched: {matched_prefs:,}')

    # 3.4 Association Snapshot (Replacement Concept IDs)
    sct_assoc = {}
    if assoc_member:
        log(f'  กำลังอ่าน SCT-Int Association Refset: {os.path.basename(assoc_member)}')
        with arc.open_tsv_lines(assoc_member) as f:
            f.readline()
            for line in f:
                parts = line.rstrip('\r\n').split('\t')
                if len(parts) >= 7 and parts[2] == '1' and parts[4] in ASSOC_REFSETS:
                    ref_cid = parts[5]
                    if ref_cid in target_vet_cids:
                        sct_assoc[ref_cid] = parts[6]
        log(f'  SCT-Int Replacements matched: {len(sct_assoc):,}')

    # 3.5 Relationship Snapshot
    sct_rels      = []
    inter_parents = {}
    inter_fs      = {}
    inter_ps      = {}
    log(f'  กำลังอ่าน SCT-Int Relationships: {os.path.basename(rel_member)}')
    with arc.open_tsv_lines(rel_member) as f:
        f.readline()
        for line in f:
            parts = line.rstrip('\r\n').split('\t')
            if len(parts) >= 8 and parts[2] == '1':
                src, dst, tid = parts[4], parts[5], parts[7]
                sct_rels.append((src, dst, tid, 'SCT_Inter'))
                if tid == IS_A_TYPE:
                    inter_parents.setdefault(src, set()).add(dst)
                elif tid == FINDING_SITE:
                    inter_fs.setdefault(src, set()).add(dst)
                elif tid in PROC_SITES:
                    inter_ps.setdefault(src, set()).add(dst)
    log(f'  SCT-Int Active Relationships: {len(sct_rels):,}')

    arc.close()
    return sct_concs, sct_descs, sct_fsn_map, sct_assoc, sct_rels, inter_parents, inter_fs, inter_ps


# ---------------------------------------------------------------------------
# Step 4: Body System (Categories) Resolution Engine
# ---------------------------------------------------------------------------
def build_body_system_resolver(fsn_map, vet_parents, vet_fs, vet_ps, inter_parents, inter_fs, inter_ps):
    body_map = dict(BODY_SYSTEM_MAP)

    # เพิ่ม children ของ Body system structure (280115004)
    for src_cid, p_set in inter_parents.items():
        if '280115004' in p_set and src_cid not in body_map:
            raw_fsn = fsn_map.get(src_cid, '')
            clean = raw_fsn.replace(' structure', '').replace(' (body structure)', '').replace(' (body system)', '').strip()
            if clean:
                body_map[src_cid] = clean

    memo = {}

    def traverse_graph(cid, parents_dict, fs_dict, ps_dict, tag):
        key = (cid, tag)
        if key in memo:
            return memo[key]

        target_sites = set()
        if cid in fs_dict:
            target_sites.update(fs_dict[cid])
        if cid in ps_dict:
            target_sites.update(ps_dict[cid])
        if not target_sites:
            target_sites.add(cid)

        resolved = set()
        for site in target_sites:
            curr_level = {site}
            visited = set()
            for _ in range(12):
                next_level = set()
                for node in curr_level:
                    if node in visited:
                        continue
                    visited.add(node)
                    if node in body_map:
                        resolved.add(body_map[node])
                    for p in parents_dict.get(node, ()):
                        next_level.add(p)
                if not next_level or resolved:
                    break
                curr_level = next_level

        res = ' | '.join(sorted(resolved)) if resolved else ''
        memo[key] = res
        return res

    def resolve(cid, sem_type):
        if cid:
            res = traverse_graph(cid, vet_parents, vet_fs, vet_ps, 'VET')
            if res:
                return res
            res = traverse_graph(cid, inter_parents, inter_fs, inter_ps, 'INTER')
            if res:
                return res

        st = (sem_type or '').lower()
        if st in ('organism', 'cell', 'life style'):
            return 'Organism / Microorganism'
        if st in ('substance', 'product', 'medicinal product', 'clinical drug', ' biologic product'):
            return 'Substance / Product'
        if st in ('qualifier value', 'foundation metadata concept', 'core metadata concept', 'attribute'):
            return 'Qualifier / Metadata'
        if st in ('physical object', 'physical force', 'environment', 'geographic location', 'event', 'situation'):
            return 'Physical Object / Environment'
        return 'Systemic / Not Applicable (N/A)'

    return resolve


# ---------------------------------------------------------------------------
# Main Build Process
# ---------------------------------------------------------------------------
def build():
    t0 = time.time()
    log('=' * 68)
    log('KAHIS Terminology Database Builder v6.0 (Update-Safe Master Engine)')
    log('=' * 68)

    sapdt_file, vsct_src, sct_src = find_sources()
    if not sapdt_file:
        log('ไม่พบไฟล์ SA-PDTReleaseFile_full_*.txt! ยกเลิกการทำงาน', 'ERROR')
        sys.exit(1)
    if not vsct_src:
        log('ไม่พบโฟลเดอร์หรือไฟล์ซิป SnomedCT_VETExtension_*! ยกเลิกการทำงาน', 'ERROR')
        sys.exit(1)
    if not sct_src:
        log('ไม่พบโฟลเดอร์หรือไฟล์ซิป SnomedCT_InternationalRF2_*! ยกเลิกการทำงาน', 'ERROR')
        sys.exit(1)

    log(f'แหล่งที่ 1 (SA-PDT) : {sapdt_file}')
    log(f'แหล่งที่ 2 (VSCT)   : {vsct_src}')
    log(f'แหล่งที่ 3 (SCT-Int): {sct_src}')

    if DRY_RUN:
        log('โหมด DRY-RUN: ตรวจพบแหล่งข้อมูลครบทั้ง 3 แหล่ง พร้อมสำหรับการสร้างฐานข้อมูล', 'INFO')
        return

    # --- Step 0: Backup & Extract Custom Data ---
    log('Step 0/6: สำรองฐานข้อมูลเดิม และดึงข้อมูล ku_synonym_text / Custom Concepts...')
    ku_synonyms_map, old_terms_map, custom_rows = backup_and_extract_existing()

    # --- Step 1: Read SA-PDT ---
    log('Step 1/6: อ่านข้อมูล SA-PDT...')
    sapdt_map = read_sapdt_file(sapdt_file)

    # --- Step 2: Read VSCT ---
    log('Step 2/6: อ่านข้อมูล VSCT (5 Snapshot Files)...')
    (
        vsct_concs, vsct_descs, vtsl_pref_dids, vsct_us_pref_dids,
        vsct_assoc, vsct_rels, vet_parents, vet_fs, vet_ps
    ) = read_vsct_archive(vsct_src)

    # Target Veterinary Concept Universe (42,299 concepts)
    target_vet_cids = set(sapdt_map.keys()) | set(vsct_concs.keys()) | set(vsct_descs.keys())
    log(f'  รวม Concept สัตวแพทย์เป้าหมายทั้งหมด (SA-PDT ∪ VSCT Conc ∪ VSCT Desc): {len(target_vet_cids):,} รหัส')

    # --- Step 3: Read SCT International ---
    log('Step 3/6: อ่านข้อมูล SNOMED CT International (5 Snapshot Files)...')
    (
        sct_concs, sct_descs, sct_fsn_map, sct_assoc,
        sct_rels, inter_parents, inter_fs, inter_ps
    ) = read_sct_archive(sct_src, target_vet_cids, vtsl_pref_dids, vsct_us_pref_dids)

    # รวม FSN Map (VSCT FSN มีความสำคัญสูงกว่า SCT-Int FSN)
    combined_fsn_map = dict(sct_fsn_map)
    for cid, vd in vsct_descs.items():
        if vd.get('fsn'):
            combined_fsn_map[cid] = vd['fsn']

    # --- Step 4: Merge & Resolve All 42,299 Concepts ---
    log('Step 4/6: ประมวลผลคัดเลือก Display Name, FSN, Synonyms, Body System และ Replacement IDs...')
    resolve_body_sys = build_body_system_resolver(
        combined_fsn_map, vet_parents, vet_fs, vet_ps, inter_parents, inter_fs, inter_ps
    )

    today_str = time.strftime('%Y-%m-%d')
    now_str   = time.strftime('%Y-%m-%d %H:%M:%S')
    merged_records = {}

    # จัดเรียงให้ SA-PDT มาก่อน ตามด้วย VSCT
    ordered_cids = list(sapdt_map.keys()) + [c for c in sorted(target_vet_cids) if c not in sapdt_map]

    for cid in ordered_cids:
        s_info = sapdt_map.get(cid)
        v_conc = vsct_concs.get(cid)
        v_desc = vsct_descs.get(cid, {})
        i_conc = sct_concs.get(cid)
        i_desc = sct_descs.get(cid, {})

        in_sapdt     = 'Yes' if s_info is not None else 'No'
        in_vsct      = 'Yes' if (v_conc is not None or bool(v_desc)) else 'No'
        in_sct_inter = 'Yes' if (i_conc is not None or cid in sct_fsn_map) else 'No'

        # 1. คัดเลือก FSN: VSCT FSN > SCT-Int FSN (Active ก่อน ตามด้วย Inactive สำหรับรหัสที่ถูกยกเลิก)
        snomed_fsn = (
            v_desc.get('fsn') or
            i_desc.get('fsn') or
            v_desc.get('inactive_fsn') or
            i_desc.get('inactive_fsn') or
            sct_fsn_map.get(cid, '')
        )
        sem_type   = extract_sem_tag(snomed_fsn)
        if not sem_type:
            # กรณีรหัสที่ถูกยกเลิกใน VSCT ยุคแรกไม่มีวงเล็บต่อท้าย FSN (เช่น ชื่อวิทยาศาสตร์ของนกแก้ว 6 รหัส)
            for pid in (vet_parents.get(cid, set()) | inter_parents.get(cid, set())):
                p_sem = extract_sem_tag(combined_fsn_map.get(pid, ''))
                if p_sem:
                    sem_type = p_sem
                    break
            if not sem_type:
                sem_type = 'organism'

        # 2. คัดเลือก SNOMED/VSCT Preferred Term:
        #    VTSL Vet Lang Refset (332501000009101) > VSCT US Lang Refset > SCT-Int US Lang Refset > FSN ตัดวงเล็บ
        snomed_pref = (
            v_desc.get('vtsl_pref') or
            i_desc.get('vtsl_pref') or
            v_desc.get('us_pref') or
            i_desc.get('us_pref') or
            strip_fsn_tag(snomed_fsn) or
            v_desc.get('inactive_syn') or
            i_desc.get('inactive_syn') or
            snomed_fsn
        )

        # 3. คัดเลือก Display Name (SA-PDT Preferred > VSCT Preferred > SCT-Int Preferred > FSN ตัดวงเล็บ)
        sapdt_pref = s_info['preferred'] if s_info else ''
        display_name = sapdt_pref or snomed_pref or strip_fsn_tag(snomed_fsn) or snomed_fsn or cid

        # 4. รวมคำพ้องภาษาอังกฤษทุกแหล่ง (Deduplicate แบบไม่สนใจตัวพิมพ์เล็ก-ใหญ่ แต่คงรูปตัวอักษรเดิม)
        snomed_syns_list = []
        seen_snomed_syns = set()
        for term in (v_desc.get('synonyms', []) + i_desc.get('synonyms', [])):
            t_low = term.lower()
            if t_low not in seen_snomed_syns:
                seen_snomed_syns.add(t_low)
                snomed_syns_list.append(term)
        snomed_all_synonyms = ' | '.join(snomed_syns_list)

        sapdt_syns_list = s_info['synonyms'] if s_info else []
        sapdt_acceptable = ' | '.join(sapdt_syns_list)

        # คอลัมน์ synonym รวมคำพ้องจากทุกแหล่ง (SA-PDT + VSCT + SCT-Int) เพื่อให้ค้นหาเจอ 100%
        unified_syns = []
        seen_unified = {display_name.lower()} if display_name else set()
        for term in ([sapdt_pref] + sapdt_syns_list + [snomed_pref] + snomed_syns_list):
            if not term:
                continue
            t_low = term.lower()
            if t_low not in seen_unified:
                seen_unified.add(t_low)
                unified_syns.append(term)
        unified_synonym_str = ' | '.join(unified_syns)

        # 5. สถานะ Active, Definition Status, Module
        conc_meta = v_conc or i_conc or {}
        snomed_active = 'Yes' if conc_meta.get('active', '1') == '1' else 'No'
        def_status    = conc_meta.get('definition_status', PRIMITIVE)
        module_id     = conc_meta.get('module') or v_desc.get('module') or i_desc.get('module') or ''

        # 6. Direct Parents & Body System (Categories)
        direct_parents = sorted(vet_parents.get(cid, set()) | inter_parents.get(cid, set()))
        parents_str    = ' | '.join(direct_parents)
        body_sys       = resolve_body_sys(cid, sem_type)

        # 7. Replacement Concept ID (สำหรับรหัสที่ถูก Retired/Inactive)
        repl_cid = vsct_assoc.get(cid) or sct_assoc.get(cid, '')

        merged_records[cid] = {
            'display_name':             display_name,
            'in_sapdt':                 in_sapdt,
            'in_vsct':                  in_vsct,
            'in_sct_inter':             in_sct_inter,
            'sapdt_concept_id':         cid if in_sapdt == 'Yes' else '',
            'sapdt_status':             s_info['status'] if s_info else '',
            'sapdt_change_type':        '',
            'sapdt_description_id':     ' | '.join(s_info['desc_ids']) if s_info else '',
            'sapdt_fsn':                sapdt_pref if s_info else '',
            'sapdt_preferred':          sapdt_pref,
            'sapdt_acceptable':         sapdt_acceptable,
            'synonym':                  unified_synonym_str,
            'sapdt_semantic_type':      sem_type if in_sapdt == 'Yes' else '',
            'snomed_concept_id':        cid,
            'snomed_fsn':               snomed_fsn,
            'snomed_preferred_term':    snomed_pref,
            'snomed_all_synonyms':      snomed_all_synonyms,
            'snomed_active':            snomed_active,
            'snomed_module':            module_id,
            'snomed_semantic_type':     sem_type,
            'body_system':              body_sys,
            'snomed_definition_status': def_status,
            'snomed_parent_concepts':   parents_str,
            'match_type':               'sapdt' if in_sapdt == 'Yes' else 'vsct_only',
            'concept_count':            '1',
            'all_snomed_concept_ids':   cid,
            'replacement_concept_id':   repl_cid,
            'match_confidence':         'Exact',
            'updated_at':               today_str,
            'updated_by':               'system_rebuild_v6',
            'created_at':               now_str,
        }

    # --- นิรภัยป้องกันรหัสกำพร้า (Zero Orphan Concepts) ---
    orphan_restored = 0
    for old_cid, old_row in old_terms_map.items():
        if old_cid not in merged_records:
            old_row['sapdt_status']  = 'Retired' if old_row.get('in_sapdt') == 'Yes' else ''
            old_row['snomed_active'] = 'No'
            old_row['replacement_concept_id'] = (
                vsct_assoc.get(old_cid) or sct_assoc.get(old_cid) or old_row.get('replacement_concept_id', '')
            )
            old_row['updated_at'] = today_str
            merged_records[old_cid] = old_row
            orphan_restored += 1

    if orphan_restored > 0:
        log(f'  กู้คืนรหัสเก่าที่ถูกถอดออกจาก Release ใหม่ (Zero Orphans): {orphan_restored:,} รหัส')

    # --- นิรภัยย้ายคำพ้อง ku ตามรหัสที่ถูกแทนที่ (Auto-Link Replacement KU Synonyms) ---
    auto_linked_ku = 0
    for (k_cid, _), (orig_cid, k_text, k_lang, k_cat) in list(ku_synonyms_map.items()):
        rec = merged_records.get(orig_cid)
        if rec and rec.get('replacement_concept_id'):
            new_cid = rec['replacement_concept_id']
            new_key = (new_cid, k_text.lower())
            if new_key not in ku_synonyms_map:
                ku_synonyms_map[new_key] = (new_cid, k_text, k_lang, k_cat)
                auto_linked_ku += 1
    if auto_linked_ku > 0:
        log(f'  เชื่อมโยงคำพ้อง ku ไปยังรหัสทดแทนอัตโนมัติ: {auto_linked_ku:,} รายการ')

    # --- Step 5: Write SQLite Database (Atomic Swap) ---
    log('Step 5/6: เขียนข้อมูลลงฐานข้อมูล SQLite (terminology_search.db)...')
    if os.path.exists(DB_TEMP):
        os.remove(DB_TEMP)

    conn = sqlite3.connect(DB_TEMP)
    cur  = conn.cursor()
    cur.execute('PRAGMA synchronous = OFF;')
    cur.execute('PRAGMA journal_mode = MEMORY;')

    # 5.1 สร้างตาราง terms (32 คอลัมน์เหมือนเดิมทุกตัวอักษร)
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

    # 5.2 สร้างตาราง relationships
    cur.execute('''CREATE TABLE relationships (
        source_id      TEXT,
        destination_id TEXT,
        type_id        TEXT,
        type_name      TEXT,
        source_release TEXT
    )''')

    # 5.3 สร้างตาราง concept_terms
    cur.execute('''CREATE TABLE concept_terms (
        concept_id   TEXT PRIMARY KEY,
        term         TEXT,
        semantic_type TEXT
    )''')

    # 5.4 สร้างตาราง ku_synonym_text
    cur.execute('''CREATE TABLE ku_synonym_text (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        concept_id      TEXT NOT NULL,
        ku_synonym_text TEXT NOT NULL,
        lang_tag        TEXT DEFAULT "ku",
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # Insert terms (ทั้งรายการมาตรฐาน + Custom Concepts ที่สร้างเอง)
    all_term_dicts = list(merged_records.values()) + custom_rows
    term_tuples = [
        (
            r.get('display_name', ''),
            r.get('in_sapdt', 'No'),
            r.get('in_vsct', 'No'),
            r.get('in_sct_inter', 'No'),
            r.get('sapdt_concept_id', ''),
            r.get('sapdt_status', ''),
            r.get('sapdt_change_type', ''),
            r.get('sapdt_description_id', ''),
            r.get('sapdt_fsn', ''),
            r.get('sapdt_preferred', ''),
            r.get('sapdt_acceptable', ''),
            r.get('synonym', ''),
            r.get('sapdt_semantic_type', ''),
            r.get('snomed_concept_id', ''),
            r.get('snomed_fsn', ''),
            r.get('snomed_preferred_term', ''),
            r.get('snomed_all_synonyms', ''),
            r.get('snomed_active', 'No'),
            r.get('snomed_module', ''),
            r.get('snomed_semantic_type', ''),
            r.get('body_system', ''),
            r.get('snomed_definition_status', PRIMITIVE),
            r.get('snomed_parent_concepts', ''),
            r.get('match_type', ''),
            r.get('concept_count', '1'),
            r.get('all_snomed_concept_ids', ''),
            r.get('replacement_concept_id', ''),
            r.get('match_confidence', ''),
            r.get('updated_at', today_str),
            r.get('updated_by', 'system_rebuild_v6'),
            r.get('created_at', now_str),
        )
        for r in all_term_dicts
    ]
    cur.executemany('''INSERT INTO terms (
        display_name, in_sapdt, in_vsct, in_sct_inter,
        sapdt_concept_id, sapdt_status, sapdt_change_type, sapdt_description_id,
        sapdt_fsn, sapdt_preferred, sapdt_acceptable, synonym, sapdt_semantic_type,
        snomed_concept_id, snomed_fsn, snomed_preferred_term, snomed_all_synonyms,
        snomed_active, snomed_module, snomed_semantic_type, body_system,
        snomed_definition_status, snomed_parent_concepts, match_type,
        concept_count, all_snomed_concept_ids, replacement_concept_id, match_confidence,
        updated_at, updated_by, created_at
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', term_tuples)
    log(f'  บันทึกตาราง terms สำเร็จ: {len(term_tuples):,} แถว')

    # Insert relationships (Deduplicate by source_id, destination_id, type_id โดยให้ VSCT มาก่อน)
    seen_rels = set()
    rel_batch = []
    rel_count = 0
    for (src, dst, tid, stag) in (vsct_rels + sct_rels):
        key = (src, dst, tid)
        if key in seen_rels:
            continue
        seen_rels.add(key)
        tname = REL_TYPE_NAMES.get(tid)
        if not tname:
            raw_t = combined_fsn_map.get(tid, '')
            tname = strip_fsn_tag(raw_t) or 'Attribute'
        rel_batch.append((src, dst, tid, tname, stag))
        rel_count += 1
        if len(rel_batch) >= 50000:
            cur.executemany('INSERT INTO relationships VALUES (?,?,?,?,?)', rel_batch)
            rel_batch = []
    if rel_batch:
        cur.executemany('INSERT INTO relationships VALUES (?,?,?,?,?)', rel_batch)
    log(f'  บันทึกตาราง relationships สำเร็จ: {rel_count:,} แถว')

    # Insert concept_terms (VSCT Priority > SCT-Int)
    ct_batch = []
    ct_count = 0
    for cid, fsn in combined_fsn_map.items():
        if not fsn:
            continue
        sem = extract_sem_tag(fsn)
        ct_batch.append((cid, fsn, sem))
        ct_count += 1
        if len(ct_batch) >= 50000:
            cur.executemany('INSERT OR IGNORE INTO concept_terms VALUES (?,?,?)', ct_batch)
            ct_batch = []
    if ct_batch:
        cur.executemany('INSERT OR IGNORE INTO concept_terms VALUES (?,?,?)', ct_batch)
    log(f'  บันทึกตาราง concept_terms สำเร็จ: {ct_count:,} แถว')

    # Insert ku_synonym_text (Restore & Sync to CSV โดยคงลำดับเดิมไว้และต่อท้ายด้วยรายการใหม่)
    ku_rows_list = list(ku_synonyms_map.values())
    if ku_rows_list:
        cur.executemany(
            'INSERT INTO ku_synonym_text (concept_id, ku_synonym_text, lang_tag, created_at) VALUES (?,?,?,?)',
            ku_rows_list
        )
    log(f'  บันทึกตาราง ku_synonym_text สำเร็จ: {len(ku_rows_list):,} แถว')

    # Sync กลับไปที่ไฟล์ ku_custom_synonyms.csv เพื่อความปลอดภัยสูงสุด
    try:
        ku_csv_out = os.path.join(APP_DIR, 'ku_custom_synonyms.csv')
        with open(ku_csv_out, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['concept_id', 'ku_synonym_text', 'lang_tag'])
            for (cid, text, lang, _) in ku_rows_list:
                writer.writerow([cid, text, lang])
    except Exception as e:
        log(f'  ไม่สามารถอัปเดตไฟล์ ku_custom_synonyms.csv: {e}', 'WARN')

    # สร้าง Indexes และ FTS5
    log('Step 6/6: สร้าง Indexes, FTS5 Search Index และบีบอัดไฟล์ .db.gz...')
    cur.execute('CREATE INDEX idx_terms_snomed ON terms (snomed_concept_id)')
    cur.execute('CREATE INDEX idx_terms_sapdt  ON terms (sapdt_concept_id)')
    cur.execute('CREATE INDEX idx_terms_display ON terms (display_name)')
    cur.execute('CREATE INDEX idx_terms_sem     ON terms (snomed_semantic_type)')
    cur.execute('CREATE INDEX idx_terms_body    ON terms (body_system)')
    cur.execute('CREATE INDEX idx_rel_src ON relationships (source_id)')
    cur.execute('CREATE INDEX idx_rel_dst ON relationships (destination_id)')
    cur.execute('CREATE INDEX idx_ku_cid  ON ku_synonym_text (concept_id)')

    try:
        cur.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS terms_fts USING fts5(
            display_name, synonym, snomed_fsn, sapdt_fsn, snomed_preferred_term, snomed_all_synonyms,
            content="terms", content_rowid="id"
        )''')
        cur.execute('INSERT INTO terms_fts(terms_fts) VALUES("rebuild")')
        log('  สร้างดัชนี FTS5 สำเร็จ')
    except Exception as e:
        log(f'  ข้ามการสร้าง FTS5: {e}', 'WARN')

    conn.commit()
    cur.execute('PRAGMA optimize;')
    conn.close()

    # Atomic Replace
    if os.path.exists(DB_OUT):
        os.replace(DB_TEMP, DB_OUT)
    else:
        os.rename(DB_TEMP, DB_OUT)

    db_size_mb = os.path.getsize(DB_OUT) / (1024 * 1024)

    # Auto Compress to .gz
    gz_out = DB_OUT + '.gz'
    log(f'  กำลังบีบอัดฐานข้อมูลเป็น {os.path.basename(gz_out)}...')
    with open(DB_OUT, 'rb') as f_in:
        with gzip.open(gz_out, 'wb', compresslevel=6) as f_out:
            shutil.copyfileobj(f_in, f_out)
    gz_size_mb = os.path.getsize(gz_out) / (1024 * 1024)

    elapsed = time.time() - t0
    log('')
    log('=' * 68)
    log(f'✅ สร้างฐานข้อมูลสำเร็จสมบูรณ์ในเวลา {elapsed:.1f} วินาที')
    log(f'   ไฟล์ฐานข้อมูล : {DB_OUT} ({db_size_mb:.1f} MB)')
    log(f'   ไฟล์บีบอัด    : {gz_out} ({gz_size_mb:.1f} MB)')
    log(f'   จำนวนข้อมูล   : terms={len(term_tuples):,} | relationships={rel_count:,} | concept_terms={ct_count:,} | ku={len(ku_rows_list):,}')
    log('=' * 68)


if __name__ == '__main__':
    build()
