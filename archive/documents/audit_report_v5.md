# KAHIS Terminology System - Comprehensive Audit Report & Updated Specification
# เอกสารรายงานผลการตรวจสอบระบบและข้อกำหนดสเปกปรับปรุง

> **เวอร์ชันเอกสาร**: 5.0.0 | **วันอัปเดต**: 2026-07-21  
> **สถานะ**: ✅ วิเคราะห์ครบถ้วน พร้อมรออนุมัติพัฒนา

---

## ส่วนที่ 1: สรุปผลการตรวจสอบเทียบ logic_structure.md

| # | ประเด็น | สถานะใน DB/Code จริง | สอดคล้อง logic_structure | ต้องแก้ไข |
|---|---------|----------------------|--------------------------|-----------|
| BUG-01 | build_search_db.py อ้างอิงไฟล์ผิด (31cols) | ❌ อ้าง 31cols ที่ถูกลบแล้ว | ❌ logic_structure กำหนด Direct-from-RF2 | ✅ ต้องแก้ |
| BUG-02 | server.py Path ผิด | ❌ glob ไม่พบ VSCT/SCT dir | ❌ ต้องใช้ Absolute/Config path | ✅ ต้องแก้ |
| BUG-03 | ตาราง custom_synonyms ไม่มี | ❌ ไม่มีในฐานข้อมูล | ❌ logic_structure กำหนดไว้ชัดเจน | ✅ ต้องแก้ |
| BUG-04 | admin.html ไม่มี | ❌ ไม่มีไฟล์ | ❌ logic_structure กำหนดไว้ชัดเจน | ✅ ต้องสร้าง |
| CONFLICT-01 | Active Filter Logic ขัดแย้ง | ❌ 339 rows ถูกซ่อนผิด | ❌ ต้องแก้ Logic | ✅ ต้องแก้ |
| CONFLICT-02 | Icon ≡/● ผิดมาตรฐาน | ❌ ใช้ semantic_type ตัดสิน | ❌ ต้องใช้ definition_status | ✅ ต้องแก้ |
| CONFLICT-03 | Children LIMIT 50 | ⚠️ มี Parent บางตัวมีลูก 3,043 | ⚠️ UI ไม่บอก total | ✅ ต้องแก้ |
| CONFLICT-04 | Synonym slice(0,5) | ❌ แสดงแค่ 5 รายการ | ❌ logic_structure ต้องการแสดงทั้งหมด | ✅ ต้องแก้ |
| SCT-01 | ไม่แยก Description Type | ⚠️ รวม `en` ทุกรายการ | ⚠️ ไม่สอดคล้องกับ SNOMED CT Browser | ✅ ต้องแก้ |
| SCT-02 | concept_terms ลำดับผิด (VSCT ถูก IGNORE) | ❌ VSCT ถูก Ignore | ❌ ลำดับ priority ผิด | ✅ ต้องแก้ |

---

## ส่วนที่ 2: วิเคราะห์เชิงลึกแต่ละประเด็น (Root Cause & Proposed Fix)

---

### 🔴 BUG-01: `build_search_db.py` อ้างอิงไฟล์ที่ถูกลบ

**Root Cause:**  
`scripts/build_search_db.py` บรรทัด 93 อ้างถึง `terminology_master_31cols.csv` ซึ่งถูกลบออกไปแล้วในการจัดระเบียบโปรเจกต์

**การแก้ไขตาม logic_structure.md:**  
ไม่ต้องแก้ไขสคริปต์นี้ เพราะตาม logic_structure กำหนดว่า DB จะถูกสร้างโดย **`build_direct_db.py`** ใหม่ทั้งหมด โดยอ่านตรงจาก 3 โฟลเดอร์ต้นฉบับ ดังนี้:

```
[ผลลัพธ์ที่ต้องการ]
build_direct_db.py อ่านจาก:
  ├── SA-PDT-Terminology-XX/          ➔ อ่าน TXT โดยตรง
  ├── SnomedCT_VETExtension_.../      ➔ อ่าน RF2 Snapshot โดยตรง  
  └── SnomedCT_InternationalRF2_.../  ➔ อ่าน RF2 Snapshot โดยตรง
  
ไม่ผ่าน CSV ใดๆ ทั้งสิ้น ➔ สร้าง terminology_search.db โดยตรง
```

**สถานะ:** `build_search_db.py` และ `build_body_system.py` ใน `scripts/` จะกลายเป็นสคริปต์ Legacy ที่เก็บไว้อ้างอิง ไม่ใช้งาน

---

### 🔴 BUG-02: `server.py` ใช้ Working Directory ผิด (Path Bug)

**Root Cause:**  
`server.py` บรรทัด 32-40 ใช้ `glob.glob('SnomedCT_VETExtension_*')` โดยไม่ระบุ base path จาก script location  
ทำให้ path ขึ้นอยู่กับว่าผู้ใช้ `cd` มาจากโฟลเดอร์ไหน ผลตรวจสอบจริงพบว่า VSCT directories = `[]` ว่างเปล่า

**ปัญหาเพิ่มเติม:**  
ระบบต้องรันได้แม้ย้ายโฟลเดอร์จาก `C:\` ไป `D:\` หรือจาก `/Users/nipon/` ไป `/Users/other/` โดยไม่แก้โค้ด

**แนวทางแก้ไขที่ถูกต้อง: ใช้ `__file__` + Config File**

```python
# วิธีที่ 1: ใช้ __file__ เพื่อหา base directory จาก server.py เสมอ
import os
APP_DIR = os.path.dirname(os.path.abspath(__file__))          # kahis-terminology-app/
KAHIS_DIR = os.path.dirname(APP_DIR)                           # kahis-terminology/

def get_release_versions():
    vsct_dirs = glob.glob(os.path.join(KAHIS_DIR, 'SnomedCT_VETExtension_*'))
    sct_dirs  = glob.glob(os.path.join(KAHIS_DIR, 'SnomedCT_InternationalRF2_*'))
    ...
```

**ผลที่ได้:**
- ย้ายโฟลเดอร์จาก `C:\` ไป `D:\` ✅ ทำงานถูกต้อง
- ย้ายจาก `/Users/nipon/` ไป `/Users/other/` ✅ ทำงานถูกต้อง  
- เปลี่ยนชื่อโฟลเดอร์ราก ✅ ทำงานถูกต้อง
- แนวทางนี้ไม่ต้องแก้โค้ดเลยเมื่อย้าย path ครับ

---

### 🔴 BUG-03: ตาราง `custom_synonyms` ไม่มีในฐานข้อมูล — การตรวจสอบชื่อคอลัมน์

**ตรวจสอบชื่อคอลัมน์ที่เกี่ยวข้องกับ Synonym ในระบบปัจจุบัน:**

| คอลัมน์ในตาราง `terms` | ความหมาย | ใช้ในการค้นหา | 
|------------------------|----------|---------------|
| `synonym` (col12) | คำพ้องจาก SA-PDT (acceptable terms คั่นด้วย `\|`) | ✅ ใช้ใน WHERE clause |
| `snomed_all_synonyms` (col17) | คำพ้องทั้งหมดจาก SNOMED RF2 (คั่นด้วย ` \| `) | ❌ ยังไม่ใช้ใน WHERE |

**ชื่อ `synonym_alias` ที่หลุดเข้ามาใน IndexedDB (production.js) เดิม:**  
ใน `production.js` ของ `terminology_builder` มีตาราง `synonym_alias` แต่ใน `terminology_search.db` ปัจจุบัน ไม่มี  
ใน logic_structure.md กำหนดชื่อตารางใหม่ว่า **`custom_synonyms`** ซึ่งเป็นชื่อที่ถูกต้องและสื่อความหมายชัดเจนกว่า

**สรุปการตั้งชื่อที่จะใช้:**

```text
terms.synonym         = คำพ้องจาก SA-PDT (ต้นฉบับ Read-Only)
terms.snomed_all_synonyms = คำพ้องจาก VSCT/SCT RF2 (ต้นฉบับ Read-Only)
custom_synonyms.synonym_text = คำพ้องประจำโครงการ ku (เพิ่มโดยทีมงาน)
```

**โครงสร้างตาราง `custom_synonyms` ที่จะสร้าง:**

```sql
CREATE TABLE custom_synonyms (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id  TEXT NOT NULL,           -- Concept ID ที่ผูก (snomed หรือ sapdt)
    synonym_text TEXT NOT NULL,           -- ข้อความคำพ้อง เช่น "cystic calculi"
    lang_tag    TEXT DEFAULT 'ku',        -- แท็กแหล่งที่มา: 'ku' = ประจำโครงการ
    created_at  DATETIME DEFAULT (datetime('now','localtime'))
);
CREATE INDEX idx_custom_syn_cid ON custom_synonyms (concept_id);
```

---

### 🔴 BUG-04: `admin.html` ยังไม่มีในโปรเจกต์

**สถานะ:** นี่คืองานหลักที่จะพัฒนาต่อ  
**สรุปฟีเจอร์ที่ต้องมีตาม logic_structure.md:**

```
admin.html
├── [🔐 PIN Modal] ป้อน 53****** ก่อนเข้าได้
├── [📊 Dashboard] แสดงสถิติ 7 รายการ
│   ├── ku synonyms count
│   ├── Total / Active / Inactive concepts
│   └── SA-PDT+VSCT / SA-PDT+SCT / VSCT-only breakdown
├── [🟢 Source Status] ตรวจจับ Version อัตโนมัติ
├── [🔨 Rebuild DB] สร้าง DB จาก 3 แหล่ง (build_direct_db.py)
├── [📥 Export master_kahis_terminology.csv] → output/
├── [📥 Export ku_custom_synonyms.csv] → output/
└── [🚀 Launch User App] เปิด index.html
```

---

### 🟠 CONFLICT-01: Logic Active Filter ขัดแย้ง

**ข้อมูลจากการตรวจสอบจริง:**

| สถานการณ์ | จำนวน rows | พฤติกรรม Logic เดิม | พฤติกรรมที่ถูกต้อง |
|-----------|-----------|---------------------|-------------------|
| SA-PDT=Active + VSCT=Active | 5,412 | ✅ แสดง | ✅ แสดง |
| SA-PDT=Active + VSCT=Inactive | 156 | ✅ แสดง (ดู SA-PDT) | ✅ แสดง (อย่างใดอย่างหนึ่ง Active) |
| SA-PDT=Retired + VSCT=Active | **339** | ❌ **ซ่อน** (ดูแค่ SA-PDT) | ✅ ควรแสดง (VSCT ยัง Active) |
| SA-PDT=Retired + VSCT=Inactive | 210 | ✅ ซ่อน | ✅ ซ่อน |

**Logic ใหม่ที่ถูกต้องตาม logic_structure.md:**  
> "ถ้าอย่างใดอย่างหนึ่งใน SA-PDT กับ VSCT มีสถานะ Active ให้ใช้งานได้"

```python
# Logic ใหม่ (เงื่อนไข Active):
WHERE (
    (in_sapdt = 'Yes' AND sapdt_status = 'Active')      -- SA-PDT Active
    OR
    (in_vsct = 'Yes' AND snomed_active = 'Yes')          -- VSCT Active
)
```

**การตรวจสอบผลข้างเคียง (Side Effects):**

| ผลข้างเคียง | วิเคราะห์ |
|-------------|-----------|
| Concept ID ที่ SA-PDT=Retired อาจถูกเพิ่ม `ku` synonym แล้วถูกซ่อน | ✅ Logic ใหม่แก้ไขแล้ว: ถ้า VSCT=Active จะแสดงปกติ |
| Concept ที่ทั้ง SA-PDT=Retired + VSCT=Inactive จะยังถูกซ่อน | ✅ ถูกต้อง ไม่มีผลข้างเคียงลบ |
| ตัวนับ "Active concepts" บน Admin Dashboard จะเปลี่ยน | ⚠️ จำนวน Active จะเพิ่ม +339 rows แต่ถูกต้องกว่าเดิม |
| filter `status=inactive` ต้องอัปเดต logic ควบคู่ไปด้วย | ✅ ต้องแก้ให้ครบทั้งสองทิศทาง |

**Logic Inactive ใหม่ที่ถูกต้อง:**

```python
# Inactive = ทั้ง SA-PDT ไม่ Active AND VSCT ไม่ Active (หรือไม่มีในทั้งสอง)
WHERE NOT (
    (in_sapdt = 'Yes' AND sapdt_status = 'Active')
    OR
    (in_vsct = 'Yes' AND snomed_active = 'Yes')
)
AND (in_sapdt = 'Yes' OR in_vsct = 'Yes')
```

---

### 🟠 CONFLICT-02: Icon `≡`/`●` ผิดมาตรฐาน SNOMED CT

**ตรวจสอบข้อมูลจริงในฐานข้อมูล:**

| Definition Status | SNOMED CT รหัส | จำนวนใน DB |
|-------------------|----------------|-----------|
| Fully Defined (≡) | 900000000000073002 | 4,720 rows |
| Primitive (○) | 900000000000074008 | 99,247 rows |

**การแตกแยกของ finding/disorder ตาม definition_status:**

| Semantic Type | Fully Defined (≡) | Primitive (○) |
|---------------|-------------------|---------------|
| disorder | 3,342 | 5,913 |
| finding | 829 | 3,255 |

**ผลสรุป:** Finding และ Disorder ส่วนใหญ่ **เป็น Primitive (○)** ไม่ใช่ Fully Defined (≡)!  
Logic เดิมใน `app.js` ที่ใช้ semantic_type ตัดสิน จึงแสดงผลผิดหลักมาตรฐาน SNOMED CT

**เปรียบเทียบกับ SNOMED CT Browser มาตรฐานสากล:**

```text
[SNOMED CT Browser Official]
  ≡  Fully Defined Concept    = definition_status = '900000000000073002'
  ○  Primitive Concept        = definition_status = '900000000000074008'

[ระบบเดิม KAHIS (ผิด)]
  ●  finding/disorder         ← ตัดสินจาก semantic_type (ผิด)
  ≡  อื่นๆ ทั้งหมด           ← (ผิด)

[ระบบใหม่ KAHIS (ถูกต้อง)]
  ≡  snomed_definition_status = '900000000000073002' (Fully Defined)
  ○  snomed_definition_status = '900000000000074008' (Primitive)
```

**โค้ดที่ต้องแก้ใน `app.js` บรรทัด 459-461:**

```javascript
// โค้ดเดิม (ผิด):
const iconHtml = (item.snomed_semantic_type === 'finding' || ...) 
    ? '<span class="icon-bullet"></span>' 
    : '<span class="icon-menu">≡</span>';

// โค้ดใหม่ (ถูกต้องตามมาตรฐาน SNOMED CT):
const isFullyDefined = item.snomed_definition_status === '900000000000073002';
const iconHtml = isFullyDefined
    ? '<span class="icon-menu" title="Fully Defined Concept">≡</span>'
    : '<span class="icon-circle" title="Primitive Concept">○</span>';
```

**หมายเหตุ:** ต้องส่งคอลัมน์ `snomed_definition_status` จาก `server.py` ใน `/api/search` response ด้วย (ปัจจุบันยังไม่ส่ง)

---

### 🟠 CONFLICT-03: Children LIMIT 50

**ข้อมูลจริง:** Parent concept บางตัวมีลูกถึง **3,043 รายการ** แต่ LIMIT ที่ 50 และ UI ไม่บอกจำนวนจริง

**แนวทางแก้ไขแบบ SNOMED CT Browser:**  
SNOMED CT Browser มาตรฐานใช้วิธี Lazy Load + แสดงจำนวน total เช่น:
```
▼ Children (3,043 concepts — showing first 50)  [Load more...]
```

**โค้ดที่ต้องแก้:**
1. `server.py`: เพิ่ม query count children จริงแยก และส่งกลับมาด้วย
2. `app.js`: แสดง `(X children — showing first 50)` และปุ่ม `[Load more]`

---

### 🟠 CONFLICT-04: Synonym แสดงเพียง 5 รายการแรก

**โค้ดปัญหาใน `app.js` บรรทัด 541:**
```javascript
data.synonyms.slice(0, 5)   // ❌ ตัดเหลือ 5 รายการแรกเสมอ
```

**แนวทางแก้ไข:**
- แสดงทั้งหมดเสมอ (ไม่มี slice)
- หรือถ้ากังวลเรื่องพื้นที่หน้าจอ ให้แสดง 10 รายการแรก + `[+ N more...]` ที่กดขยายได้

---

### 🟡 SCT-01: ไม่แยกประเภท Description Type

**เปรียบเทียบกับ SNOMED CT Browser มาตรฐาน:**

```text
[SNOMED CT Browser Official - Descriptions Tab]
Type          | Term                            | Acceptability
FSN           | Urinary bladder stone (disorder)| Not applicable
Synonym       | Bladder stone                   | Preferred (en)
Synonym       | Bladder calculus                | Acceptable (en)
Synonym       | Urolithiasis of bladder         | Acceptable (en)

[ระบบ KAHIS ปัจจุบัน]
en  Bladder stone          ← รวมหมด ไม่แยก Type
en  Bladder calculus
en  Urolithiasis of bladder

[ระบบ KAHIS ที่ควรเป็น]
[FSN]        Urinary bladder stone (disorder)
[Preferred]  Bladder stone
[Synonym]    Bladder calculus
[Synonym]    Urolithiasis of bladder
[ku]         cystic calculi          ← custom
[ku]         นิ่วในกระเพาะปัสสาวะ   ← custom
```

**แหล่งข้อมูลที่มีอยู่แล้วในตาราง `terms`:**
- `snomed_fsn` → ใช้เป็น FSN
- `snomed_preferred_term` → ใช้เป็น Preferred  
- `snomed_all_synonyms` (คั่นด้วย `|`) → ใช้เป็น Acceptable Synonyms
- `synonym` (col12 จาก SA-PDT) → Synonyms จาก SA-PDT
- `custom_synonyms.synonym_text` → `ku` custom

**ข้อสรุป:** ข้อมูลมีพร้อมแล้วในฐานข้อมูล ต้องแก้แค่ `server.py` ฝั่ง `/api/concept/` ให้แยกประเภทส่งกลับ และแก้ `app.js` ให้แสดงผล Label ที่ถูกต้อง

---

### 🟡 SCT-02: `concept_terms` ลำดับ Priority ผิด (VSCT ถูก IGNORE)

**Root Cause ใน `build_search_db.py` บรรทัด 158:**
```python
# โหลด inter_desc ก่อน vet_desc ทีหลัง
for desc_path in [inter_desc, vet_desc]:    # ❌ ลำดับผิด
    ...
    if cid not in seen_cids:               # ← ถ้า SCT Inter มีแล้ว VSCT จะถูก IGNORE
```

**การแก้ไข:**
```python
# แก้เป็น VSCT ก่อน SCT Inter
for desc_path in [vet_desc, inter_desc]:    # ✅ VSCT ก่อน (priority สูงกว่า)
```

**หมายเหตุ:** เมื่อสร้าง `build_direct_db.py` ใหม่ทั้งหมด Bug นี้จะหายไปเองเพราะจะออกแบบ Priority ใหม่ถูกต้อง

---

## ส่วนที่ 3: อัปเดต Schema คอลัมน์ใน logic_structure.md (v5.0)

### คอลัมน์ที่มีอยู่จริงในฐานข้อมูล (32 คอลัมน์)

```text
ตาราง terms (ปัจจุบัน):
col0:  id                    (INTEGER, PK)
col1:  display_name          (TEXT)
col2:  in_sapdt              (TEXT) Yes/No
col3:  in_vsct               (TEXT) Yes/No
col4:  in_sct_inter          (TEXT) Yes/No
col5:  sapdt_concept_id      (TEXT)
col6:  sapdt_status          (TEXT) Active/Retired
col7:  sapdt_change_type     (TEXT)
col8:  sapdt_description_id  (TEXT)
col9:  sapdt_fsn             (TEXT)
col10: sapdt_preferred       (TEXT)
col11: sapdt_acceptable      (TEXT)
col12: synonym               (TEXT) ← คำพ้องจาก SA-PDT คั่นด้วย |
col13: sapdt_semantic_type   (TEXT)
col14: snomed_concept_id     (TEXT)
col15: snomed_fsn            (TEXT)
col16: snomed_preferred_term (TEXT)
col17: snomed_all_synonyms   (TEXT) ← คำพ้อง VSCT/SCT Inter คั่นด้วย |
col18: snomed_active         (TEXT) Yes/No
col19: snomed_module         (TEXT)
col20: snomed_semantic_type  (TEXT)
col21: body_system           (TEXT)
col22: snomed_definition_status (TEXT) ← 900000000000073002 / 900000000000074008
col23: snomed_parent_concepts (TEXT)
col24: match_type            (TEXT)
col25: concept_count         (TEXT)
col26: all_snomed_concept_ids (TEXT)
col27: replacement_concept_id (TEXT)
col28: match_confidence      (TEXT)
col29: updated_at            (TEXT)
col30: updated_by            (TEXT)
col31: created_at            (TEXT)

ตาราง custom_synonyms (ต้องสร้างใหม่):
id          INTEGER PK
concept_id  TEXT (FK → terms.snomed_concept_id หรือ sapdt_concept_id)
synonym_text TEXT
lang_tag    TEXT DEFAULT 'ku'
created_at  DATETIME

ตาราง relationships (มีอยู่แล้ว):
source_id, destination_id, type_id, type_name, source_release

ตาราง concept_terms (มีอยู่แล้ว แต่ลำดับ Priority ผิด):
concept_id (PK), term, semantic_type
```

---

## ส่วนที่ 4: สรุปแผนการพัฒนาและลำดับการดำเนินงาน

### Phase 1: แก้ไข Bug ที่ส่งผลต่อการทำงานในปัจจุบัน (ใน `server.py` และ `app.js`)
1. **BUG-02**: แก้ `server.py` — เพิ่ม `APP_DIR` / `KAHIS_DIR` จาก `__file__`
2. **CONFLICT-01**: แก้ `server.py` — Active/Inactive Logic ใหม่ (OR condition)
3. **CONFLICT-02**: แก้ `app.js` + `server.py` — Icon ≡/○ จาก `snomed_definition_status`
4. **CONFLICT-04**: แก้ `app.js` — ลบ `slice(0,5)` ออก แสดงทั้งหมด
5. **CONFLICT-03**: แก้ `server.py` + `app.js` — Children count + Load more

### Phase 2: สร้างตาราง `custom_synonyms` และ Synonym Display (BUG-03, SCT-01)
1. สร้างตาราง `custom_synonyms` ในฐานข้อมูล
2. แก้ `/api/concept/` ให้แยก FSN / Preferred / Synonym / ku
3. แก้ `app.js` แสดง Description Type Labels ที่ถูกต้อง

### Phase 3: สร้าง `admin.html` (BUG-04)
1. หน้า Admin พร้อม PIN Modal
2. Dashboard สถิติ 7 รายการ
3. ปุ่ม Rebuild DB / Export CSV / Export ku / Launch App

### Phase 4: สร้าง `build_direct_db.py` (BUG-01, SCT-02)
1. สคริปต์ Python อ่านตรงจาก 3 โฟลเดอร์ต้นฉบับ
2. Merge Logic SA-PDT > VSCT > SCT Inter พร้อม Bug IS_A_TYPE = '116680003' ที่ถูกต้อง
3. สร้าง DB โดยตรงไม่ผ่าน CSV

---

> **หมายเหตุ**: เอกสารนี้เป็น Audit Report เวอร์ชัน 5.0 รวมกับข้อกำหนดสเปกที่อัปเดตแล้ว  
> พร้อมรออนุมัติเพื่อเริ่ม Phase 1 ได้ทันที
