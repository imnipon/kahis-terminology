# คู่มือขั้นตอนการทำงานฉบับสมบูรณ์ (KAHIS Terminology v7.0 Workflow Guide): การสร้าง อัปเดต ผสานคำพ้อง KU และการส่งออกฐานข้อมูล

เอกสารฉบับนี้อธิบายหลักการทำงานและขั้นตอนปฏิบัติงานจริง (Step-by-Step Workflow) ของระบบ **KAHIS Terminology v7.0** ครอบคลุมทั้ง 4 สถานการณ์หลัก และการส่งออกไฟล์ฐานข้อมูลเพื่อนำไปใช้งานต่อ

---

## ภาพรวมสถาปัตยกรรมการผสานข้อมูล 4 แหล่ง (Core Data Fusion Pipeline)

เมื่อสั่งรัน `scripts/build_direct_db.py` (หรือกดปุ่ม **🔨 Rebuild DB ใหม่** ในหน้า `admin.html`) ระบบจะทำงานผ่าน 6 ขั้นตอน (Steps 0–6) ดังนี้:

```text
[Step 0] ตรวจสอบและเก็บรักษาข้อมูลเดิม (Pre-Build Preservation)
   ├── อ่านตาราง ku_synonym_text จาก terminology_search.db เดิม (ถ้ามี)
   └── อ่านไฟล์ sources/4_KU-Custom/ku_synonym_text_YYYYMMDD.csv (ถ้ามี)
   ➔ นำมารวมกันโดยตัดคำซ้ำ (Union Deduplication) เตรียมไว้ในหน่วยความจำ

[Step 1] อ่านแหล่งที่ 1: SA-PDT (sources/1_SA-PDT/)
   ├── อ่านไฟล์หลัก SA-PDTReleaseFile_full_YYYYMMDD.txt (4,492 Concepts)
   └── อ่านไฟล์ส่วนต่าง SA-PDTReleaseFile_*to*.txt เพื่อเติมคอลัมน์ sapdt_change_type

[Step 2] อ่านแหล่งที่ 2: VSCT (sources/2_VSCT/)
   └── อ่าน 5 ไฟล์ Snapshot ของสัตวแพทย์ (Concepts, Descriptions, Language Refset 332501000009101, Association, Relationships)
   ➔ ได้ขอบเขตมโนทัศน์สัตวแพทย์เป้าหมายทั้งหมด (SA-PDT ∪ VSCT = 42,347 Concepts)

[Step 3] อ่านแหล่งที่ 3: SNOMED CT International (sources/3_SCT-Int/)
   └── อ่าน 5 ไฟล์ Snapshot สากล โดยดึงข้อมูลเต็มสำหรับรหัสที่ตรงกับฐานสัตวแพทย์ และดึง Global FSNs (574,677 รหัส) ลงตาราง concept_terms

[Step 4] ผสานข้อมูลตามลำดับความสำคัญ 1 > 2 > 3 (Priority Resolution & Calculation)
   ├── คัดเลือก display_name: 1. SA-PDT Preferred > 2. VSCT Preferred > 3. SCT-Int Preferred
   ├── คัดเลือก snomed_fsn  : 1. VSCT FSN > 2. SCT-Int FSN > 3. SA-PDT FSN
   ├── รวมคำพ้องภาษาอังกฤษ  : SA-PDT ∪ VSCT ∪ SCT-Int ลงคอลัมน์ synonym
   └── คำนวณ body_system (ไต่ลำดับ Is a + Finding site) และ snomed_parent_concepts

[Step 5] เขียนตารางลง SQLite + ผสานคำพ้อง KU + ฝังเลขเวอร์ชัน (Database Write & KU Merge)
   ├── เขียนตาราง terms (32 คอลัมน์), relationships, concept_terms
   ├── เขียนตาราง ku_synonym_text (ผสานคำพ้องภาษาไทยจาก Step 0 เข้ากับ Concept ID)
   └── เขียนตาราง db_metadata ฝังเลขเวอร์ชันทั้ง 4 แหล่ง (SA-PDT, VSCT, SCT, KU)

[Step 6] สร้างดัชนีค้นหา FTS5 + ส่งออกไฟล์ฐานข้อมูล 3 รูปแบบ (Indexing & Export)
   ├── 1. terminology_search.db (ไฟล์ใช้งานหลักของ Localhost Server)
   ├── 2. releases/kahis_SAPDT<v>_VSCT<v>_SCT<v>_KU<v>.db (ไฟล์สำเนาประจำรุ่นสำหรับโหลดเข้า Browser)
   └── 3. terminology_search.db.gz (ไฟล์บีบอัดขนาด ~53 MB สำหรับส่งมอบให้ทีม KAHIS Dev)
```

---

## เหตุการณ์ที่ 1: มีเฉพาะไฟล์ต้นฉบับ 3 แหล่ง สร้างฐานข้อมูลใหม่ตั้งแต่ศูนย์ (ไม่มี DB SQLite เดิม หรือทำครั้งแรกกับโปรเจกต์ใหม่)

ใช้ในกรณีที่เริ่มต้นโปรเจกต์ใหม่บนเครื่องเปล่า หรือเพิ่ง `git clone` โค้ดลงมาแล้วยังไม่มีไฟล์ `terminology_search.db` และยังไม่มีไฟล์คำพ้อง `ku` เลย

### ขั้นตอนการปฏิบัติ
1. **วางไฟล์ต้นฉบับ 3 แหล่งลงในโฟลเดอร์ `sources/`** (วางได้ทั้งแบบโฟลเดอร์ที่แตกไฟล์แล้ว หรือวางทั้งไฟล์ `.zip` โดยไม่ต้องแตกไฟล์):
   - นำไฟล์ SA-PDT (`SA-PDTReleaseFile_full_YYYYMMDD.txt`) วางใน `sources/1_SA-PDT/`
   - นำไฟล์ VSCT (`SnomedCT_VETExtension_...`) วางใน `sources/2_VSCT/`
   - นำไฟล์ SCT-Int (`SnomedCT_InternationalRF2_...`) วางใน `sources/3_SCT-Int/`
2. **สั่งสร้างฐานข้อมูลครั้งแรก (First-time Build)**:
   - รันคำสั่งใน Terminal:
     ```bash
     python scripts/build_direct_db.py
     ```
3. **สิ่งที่ระบบทำให้โดยอัตโนมัติ**:
   - ใน Step 0 ระบบจะตรวจพบว่ายังไม่มี `terminology_search.db` เดิม และยังไม่มีไฟล์ใน `sources/4_KU-Custom/` ระบบจะสร้างตาราง `ku_synonym_text` เปล่าไว้ให้ (0 รายการ) และสร้างไฟล์ตั้งต้น `sources/4_KU-Custom/ku_synonym_text_<วันที่ปัจจุบัน>.csv`
   - อ่านและผสานข้อมูลจาก 3 แหล่งตามลำดับ `1. SA-PDT > 2. VSCT > 3. SCT-Int`
   - สร้างไฟล์ `terminology_search.db`, ไฟล์บีบอัด `terminology_search.db.gz`, และไฟล์ประจำรุ่นใน `releases/kahis_SAPDT..._VSCT..._SCT..._KU....db`
4. **ตรวจสอบความถูกต้อง**:
   - รัน `python scripts/verify_db.py` (หรือเปิด `http://localhost:8080/admin.html` แล้วกดปุ่ม **🔍 ตรวจสอบความถูกต้อง DB**)

---

## เหตุการณ์ที่ 2: การนำไฟล์คำพ้อง `ku_synonym_text` ที่มีอยู่แล้ว เสริม/ผสานลงไปในฐานข้อมูล

เมื่อเรามีไฟล์คำพ้องภาษาไทย/คำย่อคลินิก มก. อยู่แล้ว (เช่น `ku_synonym_text_20261106.csv`) และต้องการนำมาผสานเข้ากับฐานข้อมูลที่ได้จาก 3 แหล่งหลัก สามารถทำได้ **2 วิธี** (ได้ผลลัพธ์เหมือนกัน 100%):

### วิธีที่ 2.1: ผสานอัตโนมัติผ่านโฟลเดอร์ `sources/4_KU-Custom/` (ตอนสร้างหรือ Rebuild DB)
1. นำไฟล์ CSV คำพ้องไปวางไว้ในโฟลเดอร์ `sources/4_KU-Custom/` โดยตั้งชื่อตามแพตเทิร์น `ku_synonym_text_YYYYMMDD.csv` (เช่น `ku_synonym_text_20261106.csv`)
2. กดปุ่ม **🔨 Rebuild DB ใหม่** ในหน้า `admin.html` (หรือรัน `python scripts/build_direct_db.py`)
3. **กลไกการผสาน**:
   - ระบบจะอ่านทุกแถวจาก `sources/4_KU-Custom/ku_synonym_text_YYYYMMDD.csv` (คอลัมน์ `concept_id`, `ku_synonym_text`, `lang_tag`)
   - นำไปบรรจุลงในตาราง `ku_synonym_text` ของ SQLite โดยผูกกับรหัส `concept_id` (ซึ่งเชื่อมกับ `snomed_concept_id` หรือ `sapdt_concept_id` ของตาราง `terms`)
   - ป้ายกำกับมุมขวาบนจะแสดงเลขเวอร์ชันของไฟล์คำพ้องเป็น `KU 20261106` ทันที

### วิธีที่ 2.2: เสริมคำพ้องเข้า DB ที่มีอยู่แล้วทันทีผ่านหน้า `admin.html` (ไม่ต้อง Rebuild ใหม่ทั้งก้อน)
1. เปิดหน้า Admin บนเครื่อง (`http://localhost:8080/admin.html`)
2. ไปที่หัวข้อ **📤 Import ku Synonyms CSV**
3. เลือกไฟล์ `.csv` จากเครื่อง แล้วกดปุ่ม **📤 Import ku Synonyms CSV**
4. **กลไกการผสาน**:
   - ระบบจะตรวจสอบคำซ้ำ (`concept_id` + `ku_synonym_text`) และแทรกเฉพาะคำพ้องใหม่ลงตาราง `ku_synonym_text` ใน `terminology_search.db` ทันทีภายในไม่ถึง 1 วินาที (ไม่ต้องรออ่านไฟล์ RF2 ใหม่)
   - พร้อมทั้งสร้างไฟล์เวอร์ชันล่าสุด `sources/4_KU-Custom/ku_synonym_text_<YYYYMMDD>.csv` และย้ายไฟล์วันที่เก่าไปเก็บใน `archive/legacy_data/` อัตโนมัติ

---

## เหตุการณ์ที่ 3: เมื่อมีต้นฉบับแหล่งใดแหล่งหนึ่ง (หรือทั้ง 3 แหล่ง) อัปเดตเวอร์ชันใหม่

เนื่องจากทั้ง 3 แหล่งออกรุ่นไม่พร้อมกัน (เช่น SA-PDT และ VSCT ออกทุกเดือนมีนาคม/กันยายน ส่วน SCT-Int ออกทุกเดือน) เมื่อมีแหล่งใดแหล่งหนึ่งออกไฟล์ใหม่ สามารถอัปเดตได้ทันทีดังนี้:

### ขั้นตอนการปฏิบัติ
1. **นำไฟล์เวอร์ชันใหม่วางลงในโฟลเดอร์ `sources/` เฉพาะแหล่งที่มีการอัปเดต**:
   - เช่น หากมีเฉพาะ **SCT-Int** ออกรุ่นใหม่ (`20261201`) ให้นำไปวางใน `sources/3_SCT-Int/` (ส่วน `1_SA-PDT`, `2_VSCT`, และ `4_KU-Custom` ใช้ของเดิมในโฟลเดอร์ได้เลย)
   - หรือหากอัปเดตทั้ง 3 แหล่ง ก็วางไฟล์ใหม่ใน `1_SA-PDT/`, `2_VSCT/`, `3_SCT-Int/`
2. **กดปุ่ม `🔨 Rebuild DB ใหม่` ในหน้า `admin.html`** (หรือรัน `python scripts/build_direct_db.py`)
3. **กลไกการทำงานอัตโนมัติ (Update-Safe 100%)**:
   - **เลือกเวอร์ชันใหม่สุดอัตโนมัติ**: สคริปต์จะสแกนหาไฟล์ที่มีเลขวันที่ `YYYYMMDD` ใหม่ที่สุดในแต่ละโฟลเดอร์ย่อยของ `sources/`
   - **รักษาคำพ้อง KU เดิม 100%**: สคริปต์จะดึงข้อมูล `ku_synonym_text` ทั้งจากฐานข้อมูลเดิมและจาก `sources/4_KU-Custom/ku_synonym_text_YYYYMMDD.csv` มารวมกันก่อนเสมอ คำพ้องภาษาไทยที่ทำสะสมไว้จึงไม่สูญหายแม้แต่คำเดียว
   - **ตรวจจับรหัสที่ถูก Retire ในรุ่นใหม่**: หากรหัสใดถูกปรับเป็น Retired ในรุ่นใหม่ ระบบจะดึงรหัสทดแทนจาก `AssociationSnapshot` มาใส่ในคอลัมน์ `replacement_concept_id` ให้โดยอัตโนมัติ
   - **สร้างไฟล์ `.db` รุ่นใหม่เก็บเข้าคลัง `releases/`**: ระบบจะบันทึกไฟล์ `.db` รุ่นใหม่โดยตั้งชื่อตามเลขเวอร์ชันของทั้ง 4 แหล่งไว้ใน `releases/` (เช่น `releases/kahis_SAPDT20260930_VSCT20260930_SCT20261201_KU20261106.db`) โดยไม่ทับไฟล์รุ่นเก่าใน `releases/` ทำให้คุณสามารถสลับโหลดไฟล์รุ่นเก่าเทียบกับรุ่นใหม่ในหน้า Browser ได้ตลอดเวลา
4. **กดปุ่ม `🔍 ตรวจสอบความถูกต้อง DB` ในหน้า `admin.html`**:
   - เพื่อรัน QA Audit 35 จุด ยืนยันความสมบูรณ์ของฐานข้อมูลรุ่นใหม่

---

## เหตุการณ์ที่ 4: การเพิ่มคำศัพท์ใหม่ลงใน `ku_synonym_text` และการส่งออก (Export SQLite DB & KU CSV)

ในการใช้งานจริง สามารถเพิ่มคำพ้องภาษาไทยหรือคำย่อคลินิกใหม่ลงใน `ku_synonym_text` ได้ **2 ช่องทางหลัก**:

### ช่องทางที่ 4.1: สัตวแพทย์/ผู้ใช้งานเสนอคำพ้องผ่านหน้าเว็บ Browser (`index.html` ➔ Cloud Firestore ➔ Admin อนุมัติ)
1. **ฝั่งผู้ใช้งาน (หน้า `index.html`)**:
   - ค้นหาและคลิกเลือก Concept ที่ต้องการ ➔ กดปุ่ม **`💡 เสนอคำพ้องภาษาไทย`** ในการ์ดขวามือ
   - พิมพ์คำพ้องภาษาไทย ชื่อผู้เสนอ และหมายเหตุคลินิก แล้วกด **`🚀 ส่งข้อเสนอคำพ้อง`**
   - ข้อมูลจะถูกส่งขึ้นไปเก็บใน **Firebase Cloud Firestore** (Collection: `ku_synonyms`, สถานะ `pending`) และแสดงป้าย `Pending (รออนุมัติ)` บนหน้าจอทันที
2. **ฝั่งผู้ดูแลระบบ (หน้า `http://localhost:8080/admin.html`)**:
   - เปิดหน้า `admin.html` ➔ ดูที่หัวข้อ **`🔥 ตรวจสอบคำพ้องที่เสนอผ่านเว็บ (Cloud Firestore Pending Queue)`**
   - กดปุ่ม **`[✅ อนุมัติเข้า DB]`** ที่รายการนั้น:
     1. ระบบจะเพิ่มคำพ้องนั้นลงตาราง `ku_synonym_text` ใน `terminology_search.db` ทันที
     2. เปลี่ยนสถานะบน Cloud Firestore จาก `pending` เป็น `approved`
     3. สร้างไฟล์เวอร์ชันวันที่ใหม่ `sources/4_KU-Custom/ku_synonym_text_<YYYYMMDD>.csv` (และย้ายไฟล์วันที่เก่าไปเก็บที่ `archive/legacy_data/`)

### ช่องทางที่ 4.2: ผู้ดูแลระบบเพิ่มหรือลบคำพ้องโดยตรงในหน้า `admin.html` (Localhost)
1. ในหน้า `admin.html` ไปที่หัวข้อ **`🌟 จัดการ ku Synonyms ในฐานข้อมูลโดยตรง`**
2. พิมพ์ `Concept ID` (เช่น `95570007`) แล้วกด **`ค้นหา`** ➔ พิมพ์ข้อความคำพ้องใหม่ แล้วกด **`➕ เพิ่ม`**
3. ระบบจะบันทึกลงตาราง `ku_synonym_text` ใน `terminology_search.db` ทันที พร้อมสร้าง/อัปเดตไฟล์ `sources/4_KU-Custom/ku_synonym_text_<YYYYMMDD>.csv` และหมุนเวียนไฟล์วันที่เก่าเข้า `archive/legacy_data/` ให้โดยอัตโนมัติ

---

## การส่งออกไฟล์ (Export Workflow) ทั้งฐานข้อมูล SQLite และไฟล์ KU Synonyms

เมื่อต้องการนำข้อมูลออกไปใช้งานจริงในระบบโรงพยาบาลสัตว์ (KAHIS) หรือสำรองข้อมูลขึ้น GitHub มีช่องทางส่งออกดังนี้:

| สิ่งที่ต้องการส่งออก | วิธีการส่งออก / ตำแหน่งไฟล์ที่ได้ | รูปแบบและการนำไปใช้งาน |
| :--- | :--- | :--- |
| **1. ฐานข้อมูล SQLite ตัวเต็ม (`.db`)** | - ไฟล์หลัก: `d:\imnipon_project\kahis-terminology\terminology_search.db`<br>- ไฟล์แยกตามรุ่น: `releases/kahis_SAPDT<v>_VSCT<v>_SCT<v>_KU<v>.db` | ขนาด ~206.6 MB มีครบทั้ง 5 ตาราง (`terms` 32 คอลัมน์, `relationships`, `concept_terms`, `ku_synonym_text`, `db_metadata`) สามารถนำไปใช้กับระบบ KAHIS หรือกดปุ่ม **`📂 โหลดไฟล์ DB จากเครื่อง`** ในหน้า Browser เพื่อทดสอบได้ทันที |
| **2. ฐานข้อมูล SQLite บีบอัด (`.db.gz`)** | ถูกสร้างอัตโนมัติทุกครั้งที่ Rebuild DB อยู่ที่:<br>`d:\imnipon_project\kahis-terminology\terminology_search.db.gz` | ขนาด ~53.6 MB (บีบอัดจาก 206.6 MB) สะดวกสำหรับการส่งไฟล์ให้ทีมพัฒนา KAHIS Dev หรือคัดลอกข้ามเครื่อง |
| **3. ไฟล์คำพ้อง `ku_synonym_text` ประจำรุ่น (`.csv`)** | - ถูกอัปเดตอัตโนมัติที่: `sources/4_KU-Custom/ku_synonym_text_YYYYMMDD.csv`<br>- หรือกดปุ่ม **`📋 Export ku Synonyms`** ในหน้า `admin.html` (จะได้ไฟล์ดาวน์โหลดและบันทึกไว้ที่ `output/ku_custom_synonyms.csv`) | มีคอลัมน์ครบถ้วน (`id, concept_id, display_name, snomed_fsn, ku_synonym_text, lang_tag, created_at`) รองรับการเปิดใน Excel (UTF-8 BOM) และใช้ Commit ขึ้น GitHub เพื่อเก็บประวัติคำพ้องภาษาไทย |
| **4. ไฟล์ตารางหลัก Master CSV 32 คอลัมน์ (`.csv`)** | กดปุ่ม **`📦 Export Master CSV`** ในหน้า `admin.html` (ดาวน์โหลดผ่านเบราว์เซอร์และบันทึกไว้ที่ `output/master_kahis_terminology.csv`) | ส่งออกข้อมูลตาราง `terms` ทั้ง 42,347 แถว ครบ 32 คอลัมน์ เป็นไฟล์ CSV สำหรับใช้วิเคราะห์ใน Excel / Python / R |
