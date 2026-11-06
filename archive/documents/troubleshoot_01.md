# Troubleshoot #01 — VSCT Concepts แสดงผลเป็น Concept ID แทนชื่อ Term

**วันที่วิเคราะห์:** 2026-07-21
**ระบบ:** KAHIS Terminology (SA-PDT & SNOMED CT Veterinary Extension)
**ไฟล์ที่เกี่ยวข้อง:** `scripts/build_direct_db.py`
**สถานะ:** RESOLVED

---

## 1. อาการ (Symptom)

Concept `25374005` (Gastroenteritis) ใน UI แสดง Children list พบรายการ:
- `34261000009105` แสดงผลเป็น **ตัวเลข ID** แทนที่จะแสดงชื่อ `Ulcerative gastroenteritis (disorder)`
- ไม่ใช่แค่รายการเดียว VSCT-only concepts หลายหมื่นรายการได้รับผลกระทบเดียวกัน

---

## 2. ขอบเขตผลกระทบ (Impact Scope)

| เมตริก | ค่า |
|---|---|
| VSCT Concepts ทั้งหมด | 37,416 |
| Concepts ที่อ่านได้จากไฟล์ `-es` (Bug) | **1,384** |
| Concepts ที่อ่านได้จากไฟล์ `-en` (ถูกต้อง) | **40,462** |
| VSCT-only terms ขาด `display_name` ใน DB | **32,749 รายการ (~91%)** |
| SA-PDT concepts ใน VSCT-en แต่ไม่ใน SCT-Int | **1,593 รายการ** |
| Children ใน relationships ที่ไม่มี FSN | **31,495 รายการ** |
| VSCT concepts ที่จะมี FSN ครบ (หลัง fix) | **37,416 (100%)** |

---

## 3. Root Cause Analysis

### Bug #1 — สาเหตุหลัก: `find_rf2()` เลือกไฟล์ Description ภาษาสเปน (`-es`) แทน (`-en`)

**บรรทัด:** `build_direct_db.py` line 311

```python
# Bug: pattern ไม่ระบุภาษา ทำให้ glob เลือกไฟล์ผิด
vsct_desc_path = find_rf2(vsct_dir, 'sct2_Description_Snapshot*.txt')
```

ฟังก์ชัน `find_rf2()` ใช้ `glob.glob()` แล้วคืนค่า `hits[0]` เสมอ:

```python
def find_rf2(base_dir, pattern):
    hits = glob.glob(os.path.join(base_dir, '**', pattern), recursive=True)
    return hits[0] if hits else None
```

ในโฟลเดอร์ VSCT มีไฟล์ Description Snapshot 3 ไฟล์:

| glob order | ไฟล์ | ภาษา | Concepts |
|---|---|---|---|
| **[0] เลือกใช้ (ผิด!)** | `sct2_Description_Snapshot-es_...txt` | สเปน | 1,384 |
| [1] | `sct2_Description_Snapshot-it_...txt` | อิตาลี | — |
| [2] | `sct2_Description_Snapshot-en_...txt` | **อังกฤษ** | **40,462** |

หมายเหตุ: `glob.glob()` ไม่รับประกัน sort order ขึ้นอยู่กับ filesystem ของระบบ ทำให้ผลลัพธ์ไม่แน่นอนระหว่างเครื่อง

---

### Bug #2 — Step 4b: ดึง FSN จาก `sct_descs` เท่านั้น ไม่ Fallback ไป `vsct_descs`

**บรรทัด:** `build_direct_db.py` lines 392-396

```python
# Bug: VSCT Extension concepts จะไม่มีใน sct_descs
eng_desc  = sct_descs.get(snomed_cid, {})
fsn       = eng_desc.get('fsn', '')          # => '' (ว่าง)
preferred = eng_desc.get('preferred', '') or fsn  # => ''
```

ผลลัพธ์: `display_name = preferred or fsn or snomed_cid` => ได้เป็น snomed_cid (ID ดิบ)

---

### Bug #3 — Step 4a: SA-PDT merge ไม่ Fallback ไป `vsct_descs` เช่นกัน

**บรรทัด:** `build_direct_db.py` line 353

```python
# Bug: SA-PDT concepts ที่เป็น VSCT Extension จะไม่ได้รับ snomed_fsn
eng_desc = sct_descs.get(snomed_cid)
if eng_desc:  # => None สำหรับ VSCT-specific concepts
    rec['snomed_fsn'] = ...
```

ผลกระทบน้อยกว่า Bug #1/#2 เพราะ SA-PDT concepts ยังมี `sapdt_preferred`/`sapdt_fsn` เป็น fallback

---

## 4. Data Flow เปรียบเทียบ (Before / After Fix)

### ก่อน Fix
```
glob('sct2_Description_Snapshot*.txt')
  => hits[0] = sct2_Description_Snapshot-es_...txt  (สเปน)
  => vsct_descs = {1,384 concepts}

Step 4b: VSCT-only (34261000009105)
  sct_descs.get('34261000009105') => {}  (ไม่อยู่ใน SCT-Int)
  vsct_descs.get('34261000009105') => {}  (ไม่อยู่ในไฟล์สเปน)
  => fsn = ''
  => display_name = '34261000009105'  <- แสดงเป็น ID ดิบ
```

### หลัง Fix
```
glob('sct2_Description_Snapshot-en*.txt')
  => hits[0] = sct2_Description_Snapshot-en_...txt  (อังกฤษ)
  => vsct_descs = {40,462 concepts}

Step 4b: VSCT-only (34261000009105)
  sct_descs.get('34261000009105') => {}  (ไม่อยู่ใน SCT-Int)
  vsct_descs.get('34261000009105') => {fsn: 'Ulcerative gastroenteritis (disorder)'}
  => fsn = 'Ulcerative gastroenteritis (disorder)'
  => display_name = 'Ulcerative gastroenteritis (disorder)'  <- ถูกต้อง!
```

---

## 5. การแก้ไข (Fix Applied)

### Fix #1 — `build_direct_db.py` line 311

```diff
- vsct_desc_path = find_rf2(vsct_dir, 'sct2_Description_Snapshot*.txt')
+ # FIX-01: บังคับใช้ไฟล์ภาษาอังกฤษ (-en) เป็น primary
+ vsct_desc_path = (
+     find_rf2(vsct_dir, 'sct2_Description_Snapshot-en*.txt') or
+     find_rf2(vsct_dir, 'sct2_Description_Snapshot*.txt')
+ )
```

### Fix #2 — `build_direct_db.py` lines 392-396

```diff
- eng_desc  = sct_descs.get(snomed_cid, {})
- fsn       = eng_desc.get('fsn', '')
- preferred = eng_desc.get('preferred', '') or fsn
- vsct_syns = vsct_descs.get(snomed_cid, {}).get('synonyms', [])
- all_syns  = eng_desc.get('synonyms', []) + vsct_syns
+ # FIX-02: Fallback ไป vsct_descs เมื่อไม่พบใน sct_descs (SCT-Int)
+ sct_desc  = sct_descs.get(snomed_cid, {})
+ vsct_desc = vsct_descs.get(snomed_cid, {})
+ fsn       = sct_desc.get('fsn', '') or vsct_desc.get('fsn', '')
+ preferred = (sct_desc.get('preferred', '') or sct_desc.get('fsn', '') or
+              vsct_desc.get('preferred', '') or vsct_desc.get('fsn', ''))
+ vsct_syns = vsct_desc.get('synonyms', [])
+ all_syns  = sct_desc.get('synonyms', []) + vsct_syns
```

### Fix #3 — `build_direct_db.py` lines 353-360

```diff
- # English FSN/Preferred from SCT-Int
- eng_desc = sct_descs.get(snomed_cid)
- if eng_desc:
-     rec['snomed_fsn']            = eng_desc.get('fsn', '')
-     rec['snomed_preferred_term'] = eng_desc.get('preferred', '') or eng_desc.get('fsn', '')
-     rec['snomed_module']         = eng_desc.get('module', '')
-     vsct_syns = vsct_descs.get(snomed_cid, {}).get('synonyms', [])
-     all_syns  = eng_desc.get('synonyms', []) + vsct_syns
-     rec['snomed_all_synonyms']   = ' | '.join(all_syns)
+ # FIX-03: English FSN/Preferred from SCT-Int with fallback to VSCT-en
+ sct_desc  = sct_descs.get(snomed_cid) or {}
+ vsct_desc = vsct_descs.get(snomed_cid) or {}
+ best_desc = sct_desc if sct_desc.get('fsn') else vsct_desc
+ if best_desc.get('fsn'):
+     rec['snomed_fsn']            = best_desc.get('fsn', '')
+     rec['snomed_preferred_term'] = best_desc.get('preferred', '') or best_desc.get('fsn', '')
+     rec['snomed_module']         = best_desc.get('module', '')
+     vsct_syns = vsct_desc.get('synonyms', [])
+     all_syns  = sct_desc.get('synonyms', []) + vsct_syns
+     rec['snomed_all_synonyms']   = ' | '.join(all_syns)
```

---

## 6. ผล Health Check หลัง Rebuild (2026-07-21)

Rebuild เสร็จใน **35.0 วินาที**

### Build Log Summary
```
[INFO]   VSCT desc file: sct2_Description_Snapshot-en_INT1000009_20260331.txt
[INFO] SA-PDT concepts: 4,489
[INFO] VSCT-only added: 35,817
[INFO] Total records:   40,306
[INFO]   terms: 40,306 rows inserted
[INFO]   relationships: 1,357,048 rows inserted
[INFO]   concept_terms: 568,744 rows inserted
[INFO] Build complete in 35.0s
```

### SQL Health Check Results

| Query | ผลลัพธ์ | เป้าหมาย | สถานะ |
|---|---|---|---|
| Q1 broken display_name in terms | **0** | 0 | PASS |
| Q5 VSCT-only terms no FSN | **0** | 0 | PASS |
| Q3 concept 34261000009105 display_name | `Ulcerative gastroenteritis (disorder)` | ชื่อ Term | PASS |
| Q2 VSCT-only (32,749 terms) showing_id | **0** | 0 | PASS |
| Q2 SA-PDT+VSCT (1,593 terms) showing_id | **0** | 0 | PASS |

### หมายเหตุเพิ่มเติม
Children ของ Gastroenteritis ที่เป็น **SCT-International only** (ไม่ใช่ SA-PDT/VSCT) เช่น:
- `240332005` Infantile gastroenteritis
- `12463005` Infectious gastroenteritis
- `69776003` Acute gastroenteritis

ไม่อยู่ใน `terms` table (โดย design — terms ครอบคลุมเฉพาะ SA-PDT + VSCT)
แต่ `server.py` `get_concept_meta()` มี fallback ไปที่ `concept_terms` table ซึ่งมีข้อมูลครบ
ดังนั้น UI แสดงผลถูกต้องผ่าน fallback mechanism ที่มีอยู่แล้ว

---

## 7. SQL Health Check Queries (สำหรับ Rebuild ครั้งต่อไป)

```sql
-- Q1: terms ที่ยังแสดงเป็น ID (เป้าหมาย: 0)
SELECT COUNT(*) as broken_terms
FROM terms
WHERE display_name = snomed_concept_id
   OR display_name = sapdt_concept_id;

-- Q2: FSN coverage แยกตามแหล่งที่มา
SELECT in_sapdt, in_vsct, in_sct_inter,
       COUNT(*) as total,
       SUM(CASE WHEN snomed_fsn != '' THEN 1 ELSE 0 END) as has_fsn,
       SUM(CASE WHEN display_name = snomed_concept_id THEN 1 ELSE 0 END) as showing_id
FROM terms
GROUP BY in_sapdt, in_vsct, in_sct_inter
ORDER BY total DESC;

-- Q3: ตรวจ concept 34261000009105
SELECT snomed_concept_id, display_name, snomed_fsn, snomed_preferred_term, in_vsct
FROM terms
WHERE snomed_concept_id = '34261000009105';

-- Q4: Children ของ Gastroenteritis (25374005) — ตรวจรวม concept_terms
SELECT r.source_id,
       COALESCE(t.display_name, ct.term, r.source_id) as display_name,
       CASE WHEN t.snomed_concept_id IS NOT NULL THEN 'terms'
            WHEN ct.concept_id IS NOT NULL THEN 'concept_terms'
            ELSE 'MISSING' END as source
FROM relationships r
LEFT JOIN terms t ON t.snomed_concept_id = r.source_id
LEFT JOIN concept_terms ct ON ct.concept_id = r.source_id
WHERE r.destination_id = '25374005'
  AND r.type_id = '116680003'
ORDER BY display_name;

-- Q5: VSCT-only terms ที่ไม่มี FSN (เป้าหมาย: 0)
SELECT COUNT(*) as no_fsn_count
FROM terms
WHERE in_vsct = 'Yes' AND in_sapdt = 'No' AND snomed_fsn = '';
```

---

## ✅ สรุปผลการดำเนินงาน

**วันที่ดำเนินการ:** 2026-07-21 16:38 (ICT)

### สถานะ DB ปัจจุบัน

| รายการ | รายละเอียด |
|---|---|
| ไฟล์ DB | `terminology_search.db` (204 MB) |
| Timestamp | 2026-07-21 16:38 |
| สถานะ | **Rebuilt แล้ว — ใช้งานได้ทันที** |
| ไฟล์ GZ | `terminology_search.db.gz` (51 MB) — compressed ใหม่แล้ว |
| Build time | 35.0 วินาที |

> **ไม่จำเป็นต้องสั่ง rebuild ผ่าน admin.html อีกครั้ง**
> DB ที่ได้จากการรัน script โดยตรงและจาก admin.html เป็นกระบวนการเดียวกัน
> (`server.py` เรียก `build_direct_db.py` ผ่าน subprocess เมื่อกด Rebuild ใน admin UI)

---

### ไฟล์ที่เปลี่ยนแปลง

| ไฟล์ | การเปลี่ยนแปลง |
|---|---|
| `scripts/build_direct_db.py` | แก้ไข 3 จุด (Fix #1, #2, #3) |
| `terminology_search.db` | Rebuilt ใหม่ทั้งหมด (2026-07-21 16:38) |
| `terminology_search.db.gz` | Compressed ใหม่ตาม DB ที่ rebuilt |
| `troubleshoot_01.md` | เอกสาร troubleshoot นี้ |

---

### รายละเอียดการแก้ไขใน `build_direct_db.py`

#### Fix #1 — Line 311: บังคับโหลดไฟล์ VSCT ภาษาอังกฤษ (`-en`)

```python
# BEFORE (Bug): glob เลือกไฟล์ -es (สเปน) เป็น hits[0]
vsct_desc_path = find_rf2(vsct_dir, 'sct2_Description_Snapshot*.txt')

# AFTER (Fix): ระบุ -en pattern โดยตรง พร้อม fallback
vsct_desc_path = (
    find_rf2(vsct_dir, 'sct2_Description_Snapshot-en*.txt') or
    find_rf2(vsct_dir, 'sct2_Description_Snapshot*.txt')
)
log(f'  VSCT desc file: {os.path.basename(vsct_desc_path)}')
```

**ผลลัพธ์:** `vsct_descs` มี **40,462** concepts (จากเดิม 1,384)

---

#### Fix #2 — Lines 392–396: Step 4b fallback `sct_descs → vsct_descs`

```python
# BEFORE (Bug): VSCT Extension concepts ไม่มีใน sct_descs => fsn=""
eng_desc  = sct_descs.get(snomed_cid, {})
fsn       = eng_desc.get('fsn', '')
preferred = eng_desc.get('preferred', '') or fsn

# AFTER (Fix): priority SCT-Int => VSCT-en
sct_desc  = sct_descs.get(snomed_cid, {})
vsct_desc = vsct_descs.get(snomed_cid, {})
fsn       = sct_desc.get('fsn', '') or vsct_desc.get('fsn', '')
preferred = (sct_desc.get('preferred', '') or sct_desc.get('fsn', '') or
             vsct_desc.get('preferred', '') or vsct_desc.get('fsn', ''))
vsct_syns = vsct_desc.get('synonyms', [])
all_syns  = sct_desc.get('synonyms', []) + vsct_syns
```

**ผลลัพธ์:** concept `34261000009105` ได้รับ FSN = `Ulcerative gastroenteritis (disorder)`

---

#### Fix #3 — Lines 353–360: Step 4a fallback `sct_descs → vsct_descs`

```python
# BEFORE (Bug): SA-PDT concepts ที่เป็น VSCT Extension ไม่ได้รับ snomed_fsn
eng_desc = sct_descs.get(snomed_cid)
if eng_desc:  # => None สำหรับ VSCT-specific concepts
    rec['snomed_fsn'] = eng_desc.get('fsn', '')
    ...

# AFTER (Fix): ใช้ best_desc จาก SCT-Int หรือ VSCT-en
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
```

**ผลลัพธ์:** SA-PDT concepts ที่เป็น VSCT Extension ได้รับ `snomed_fsn` ถูกต้อง 1,593 รายการ

---

### ผล Health Check (รันหลัง Rebuild 2026-07-21 16:38)

| Query | ก่อน Fix | หลัง Fix | เป้าหมาย |
|---|---|---|---|
| Q1 — `display_name` เป็น ID ดิบ | **32,750** | **0** | 0 ✅ |
| Q2 — VSCT-only `showing_id` | **32,749** | **0** | 0 ✅ |
| Q2 — SA-PDT+VSCT `showing_id` | **1,593** | **0** | 0 ✅ |
| Q3 — `34261000009105` display_name | `34261000009105` | `Ulcerative gastroenteritis (disorder)` | ชื่อ Term ✅ |
| Q5 — VSCT-only ไม่มี FSN | **32,749** | **0** | 0 ✅ |

### Build Statistics เปรียบเทียบ

| ตัวเลข | ก่อน Fix | หลัง Fix |
|---|---|---|
| VSCT desc concepts โหลดได้ | 1,384 | **40,462** |
| terms inserted | 40,306 | 40,306 (เท่าเดิม) |
| relationships inserted | 1,357,048 | 1,357,048 |
| concept_terms inserted | 535,762 | **568,744** (+32,982) |
| Build time | ~35s | ~35s |

---

### แนวทางเปรียบเทียบกับ Admin UI Build

เมื่อต้องการ verify ผลจาก admin.html:

1. **Backup DB ที่ fixed แล้ว:**
   ```bash
   cp terminology_search.db terminology_search.db.fixed_backup
   ```

2. **Rebuild ผ่าน admin.html** ตามปกติ

3. **ใช้ SQL Q1–Q5** (ดูหัวข้อ 7) ตรวจสอบ — ควรได้ค่าเดียวกันทุก query

4. **ถ้าผลต่าง** — แสดงว่า admin.html อาจเรียก script เวอร์ชันเก่า (cache) หรือ subprocess มีปัญหา

---

---

## 8. Baseline Snapshot & Backup Records (2026-07-21 17:28)

### ไฟล์ Backup ที่ถูกบันทึกไว้ (`kahis-terminology-app/backup/`)
- `terminology_search_20260721_172842.db` (203.6 MB)
- `terminology_search_20260721_172842.db.gz` (50.9 MB)

### ข้อมูลตรวจสอบความถูกต้องก่อน Rebuild ทดลอง (Baseline Metrics)

| รายการ | ค่าอ้างอิง (Baseline) |
|---|---|
| ขนาดไฟล์ DB | 203.6 MB |
| ขนาดไฟล์ GZ | 50.9 MB |
| ตาราง `terms` | 40,306 แถว |
| ตาราง `relationships` | 1,357,048 แถว |
| ตาราง `concept_terms` | 568,744 แถว |
| Q1: Terms แสดงเป็น Concept ID ดิบ | **0** |
| Q5: VSCT-only terms ขาด FSN | **0** |
| Q3: Concept `34261000009105` display_name | `Ulcerative gastroenteritis (disorder)` |

### ตารางแยกสถิติตามแหล่งที่มา (Source Breakdown Baseline)

| SA-PDT | VSCT | SCT-Int | Total Terms | Has FSN | Showing ID |
|:---:|:---:|:---:|:---:|:---:|:---:|
| No | Yes | No | **32,749** | 32,749 (100%) | **0** |
| No | Yes | Yes | **3,068** | 3,068 (100%) | **0** |
| Yes | No | Yes | **2,890** | 2,890 (100%) | **0** |
| Yes | Yes | No | **1,593** | 1,593 (100%) | **0** |
| Yes | Yes | Yes | **6** | 6 (100%) | **0** |
