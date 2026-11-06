# คู่มือการดาวน์โหลดไฟล์ต้นฉบับและรายงานวิเคราะห์การอัปเดตฐานข้อมูลรุ่นใหม่ (`SA-PDT 20260930` | `VSCT 20260930` | `SCT-Int 20261101`)

> **วันที่จัดทำเอกสาร:** 6 พฤศจิกายน 2026  
> **วัตถุประสงค์:** บันทึกหลักการดาวน์โหลดไฟล์ข้อมูลจากเว็บไซต์ VTSL (`https://vtsl.vetmed.vt.edu/sa/Documents/`) เปรียบเทียบความแตกต่างของไฟล์แต่ละรูปแบบ สรุปความเปลี่ยนแปลงของข้อมูลรุ่นใหม่ (`20260930` / `20261101`) เทียบกับรุ่นก่อนหน้า (`20260331` / `20260701`) และแนวทางการปรับปรุงสคริปต์เพื่อรองรับการอัปเดตในอนาคต

---

## 1. วิเคราะห์หลักการดาวน์โหลดข้อมูลจากหน้าเว็บ VTSL (`SA-PDT`)

จากการตรวจสอบหน้าเว็บไซต์ของ **Virginia-Maryland College of Veterinary Medicine — Veterinary Terminology Services Laboratory (VTSL)** ที่ URL `https://vtsl.vetmed.vt.edu/sa/Documents/` ในส่วนของ **Small Animal Patient Description Terminology (SA-PDT)** พบว่ามีลิงก์ให้ดาวน์โหลดทั้งหมด **5 รายการ** ซึ่งมีรูปแบบไฟล์และพฤติกรรมของเบราว์เซอร์แตกต่างกันดังนี้:

| ลำดับ | ชื่อลิงก์บนหน้าเว็บ VTSL | ชื่อไฟล์ / URL ปลายทาง | ประเภทเนื้อหา (`Content-Type`) และพฤติกรรมเมื่อคลิกซ้าย | ขนาด / จำนวนข้อมูล (รุ่น `20260930`) | แนวทางการนำมาใช้งานในโปรเจกต์ |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | **Full Release Package** | `SA-PDT Sep 2026 Release.zip` | `application/zip`<br>เบราว์เซอร์ดาวน์โหลดลงเครื่องเป็นไฟล์ `.zip` ทันที | `627 KB`<br>ข้างในประกอบด้วยไฟล์ **XML 2 ไฟล์**:<br>• `ReleaseFile_full_20260930.xml` (`7.2 MB`)<br>• `ReleaseFile_20260331to20260930.xml` (`65 KB`)<br>• `releaseFormat2_5.xsd` & `Documentation.doc` | **เป็นรูปแบบมาตรฐานใหม่ของ VTSL (XML Format v2.5)**<br>*ข้อสังเกตสำคัญ:* ภายในไฟล์ `.zip` นี้ **ไม่มีไฟล์ `.txt`** อยู่ข้างใน เนื่องจาก VTSL แจ้งว่าจะยุติการรวมไฟล์รูปแบบเก่าไว้ในแพ็กเกจ `.zip` |
| **2** | **Browser Viewable - FULL Subset** | `SA-PDTReleaseFile_full_20260930.cfm` | `text/html;charset=UTF-8`<br>หน้าเว็บ ColdFusion แสดงตาราง HTML บนเบราว์เซอร์ | `2.61 MB` (HTML Table) | ใช้สำหรับเปิดดูด้วยตาเปล่าบนเว็บเบราว์เซอร์เท่านั้น **ไม่ใช้ในการสร้างฐานข้อมูล** |
| **3** | **Browser Viewable - Changes** | `SA-PDTReleaseFile_20260331to20260930.cfm` | `text/html;charset=UTF-8`<br>หน้าเว็บ ColdFusion แสดงตาราง HTML เฉพาะรายการที่เปลี่ยนแปลง | `37.9 KB` (HTML Table) | ใช้สำหรับเปิดดูรายการเปลี่ยนแปลงด้วยตาเปล่าบนเบราว์เซอร์ |
| **4** | **Tab Delimited - FULL Subset** | `SA-PDTReleaseFile_full_20260930.txt` | `text/plain` (`Content-Disposition: null`)<br>**เมื่อคลิกซ้าย เบราว์เซอร์จะเปิดแสดงข้อความในแท็บใหม่แทนการดาวน์โหลดเป็นไฟล์** | `534,443 bytes`<br>(**`8,010` แถวคำศัพท์** / **`4,492` Concepts**) | **ไฟล์ตารางหลัก (Tab-Delimited TSV)** สำหรับนำเข้าสู่ `sources/1_SA-PDT/`<br>*วิธีบันทึกไฟล์:* คลิกขวาที่ลิงก์ ➔ เลือก **"บันทึกลิงก์เป็น..." (Save link as...)** หรือเมื่อเปิดแท็บแล้วกด `Ctrl + S` |
| **5** | **Tab Delimited - Changes** | `SA-PDTReleaseFile_20260331to20260930.txt` | `text/plain` (`Content-Disposition: null`)<br>เปิดแสดงข้อความในแท็บเมื่อคลิกซ้าย | `5,384 bytes`<br>(**`67` แถว** / **`28` Concepts** ที่มีการเปลี่ยนแปลง) | **ไฟล์ Delta บันทึกการเปลี่ยนแปลง** ใช้สำหรับดึงค่า `CHANGETYPE` ไปเติมลงในคอลัมน์ `sapdt_change_type` ของตาราง `terms` |

### โครงสร้างคอลัมน์ในไฟล์ `.txt` เทียบกับแท็กในไฟล์ `.xml` ของ SA-PDT

ทั้งไฟล์ `SA-PDTReleaseFile_full_YYYYMMDD.txt` และ `ReleaseFile_full_YYYYMMDD.xml` มีข้อมูลชุดเดียวกันทุกประการ โดยจับคู่ฟิลด์ได้ดังนี้:

| คอลัมน์ในไฟล์ `.txt` (Tab-Delimited) | แท็กในไฟล์ `.xml` (`releaseFormat2_5.xsd`) | ความหมายและการนำไปใช้ |
| :--- | :--- | :--- |
| `Concept Identifier` / `CONCEPTID` | `<Concept><ConceptID>` | รหัส SNOMED CT Concept ID (เช่น `70650003`) |
| `SNOMED Status` / `SNOMEDSTATUS` | `<Concept><Status>` | สถานะของ Concept ใน SA-PDT (`Active` หรือ `Retired`) |
| `Description Status` / `DESCSTATUS` | `<Description><Status>` | สถานะของคำศัพท์ (`Active` หรือ `Retired`) |
| `Description Identifier` / `DESCRIPTIONID` | `<Description><DescriptionID>` | รหัส Description ID ของคำศัพท์นั้น |
| `Term` / `TERM` | `<Description><Term>` | ข้อความคำศัพท์ภาษาอังกฤษ (เช่น `Bladder stone`) |
| `Term Designation` / `ISDISPLAY` | `<Description><IsDisplay>` | ประเภทคำศัพท์: `Preferred` (คำหลัก) หรือ `Acceptable` (คำพ้อง) |
| `CHANGETYPE` *(เฉพาะไฟล์ Changes)* | `<ChangeType>` *(เฉพาะไฟล์ Changes)* | ประเภทการเปลี่ยนแปลงในรอบ Release (`New Concept`, `Retired Concept`, ฯลฯ) |

> [!TIP]
> **การออกแบบเพื่อรองรับอนาคต (Future-Proofing):**  
> เราได้ออกแบบให้สคริปต์ `build_direct_db.py` รองรับการอ่าน**ทั้งไฟล์ `.txt` (`SA-PDTReleaseFile_full_*.txt`) และไฟล์ `.xml` (`ReleaseFile_full_*.xml`)** โดยอัตโนมัติ ดังนั้นในอนาคตหาก VTSL ถอดลิงก์ `.txt` ออกและเหลือเพียงไฟล์ `.zip` ที่มีแต่ `.xml` ระบบของเราก็ยังสามารถสร้างฐานข้อมูลได้ทันทีโดยไม่ต้องแก้ไขโค้ด

---

## 2. เปรียบเทียบข้อมูลรุ่นเก่า (`20260331` / `20260701`) กับรุ่นใหม่ (`20260930` / `20261101`)

จากการตรวจสอบชุดไฟล์ที่ดาวน์โหลดไว้ในโฟลเดอร์ `C:\Users\PC-DIAG\Downloads\Download Terminology 6nov2026` เทียบกับฐานข้อมูลรุ่นก่อนหน้า พบรายละเอียดการเปลี่ยนแปลงดังนี้:

### 2.1 ตารางเปรียบเทียบสถิติทั้ง 3 แหล่งข้อมูล

| แหล่งข้อมูล (Source) |ไฟล์ / ตารางย่อย | รุ่นเก่า (`20260331` / `20260701`) | รุ่นใหม่ (`20260930` / `20261101`) | ส่วนต่าง (Delta) และรายละเอียดสำคัญ |
| :--- | :--- | ---: | ---: | :--- |
| **1. SA-PDT** | จำนวนแถวคำศัพท์ทั้งหมด | `8,009` แถว | **`8,010` แถว** | `+1` แถวสุทธิ (มีการเพิ่มคำศัพท์ใหม่และถอดคำเก่าออกตามไฟล์ Changes `67` แถว) |
| | จำนวน Concept ทั้งหมด | `4,489` รหัส | **`4,492` รหัส** | **`+3` Concepts ใหม่** |
| | • สถานะ `Active` | `4,103` รหัส | **`4,103` รหัส** | คงที่ (`+3` รหัสใหม่ และมีรหัสเดิมเปลี่ยนเป็น `Retired` สุทธิ `3` รหัส) |
| | • สถานะ `Retired` | `386` รหัส | **`389` รหัส** | **`+3` รหัส Retired** |
| **2. VSCT** (`INT1000009`) | `sct2_Concept_Snapshot` | `37,416` แถว | **`37,445` แถว** | **`+29` Concepts สัตวแพทย์ใหม่** |
| | `sct2_Description_Snapshot-en` | `102,581` แถว | **`104,268` แถว** | **`+1,687` คำศัพท์/คำพ้องภาษาอังกฤษ** |
| | `sct2_Relationship_Snapshot` | `63,161` แถว | **`69,043` แถว** | **`+5,882` ความสัมพันธ์** |
| | `der2_cRefset_LanguageSnapshot-en` | `179,853` แถว | **`185,988` แถว** | **`+6,135` รายการระบุความสำคัญของภาษา (Preferred/Acceptable)** |
| | `der2_cRefset_AssociationSnapshot` | `3,833` แถว | **`4,555` แถว** | **`+722` รายการเชื่อมโยงรหัสทดแทน (Replacement IDs)** |
| **3. SCT-Int** | `sct2_Concept_Snapshot` | รุ่น `20260701` | **`540,351` แถว** (`20261101`) | อัปเดตสู่รุ่น `20261101T120000Z` |
| | `sct2_Description_Snapshot-en` | — | **`1,739,054` แถว** | คำศัพท์มาตรฐานสากลภาษาอังกฤษ |
| | `sct2_Relationship_Snapshot` | — | **`3,625,255` แถว** | โครงสร้างความสัมพันธ์แม่-ลูกและคุณลักษณะ |
| | `der2_cRefset_LanguageSnapshot-en` | — | **`3,404,379` แถว** | ข้อมูลระบุ US/GB Preferred Terms |
| | `der2_cRefset_AssociationSnapshot` | — | **`228,114` แถว** | ข้อมูลรหัสทดแทนมาตรฐานสากล |

### 2.2 รายละเอียดการเปลี่ยนแปลงใน `SA-PDT 20260331to20260930` (28 Concepts / 67 แถว)

จากการวิเคราะห์ไฟล์ `SA-PDTReleaseFile_20260331to20260930.txt` พบการเปลี่ยนแปลงแบ่งเป็น 5 ประเภท (`CHANGETYPE`):

1. **`New Concept` (เพิ่มรหัสโรคใหม่เข้าสู่ SA-PDT จำนวน 3 Concepts / 7 แถว):**
   - `1386301009`: **Chronic Enteropathy** *(Preferred)* / Chronic enteropathy *(Acceptable)*
   - `6995000`: **Fracture of deciduous tooth** *(Preferred)* / Deciduous tooth fracture *(Acceptable)*
   - `10679007`: **Fracture of permanent tooth** *(Preferred)* / Permanent tooth fracture *(Acceptable)*
2. **`Retired Concept` (ยกเลิกรหัสโรคใน SA-PDT จำนวน 4 Concepts / 9 แถว):**
   - `58265007`: *Fracture of tooth* (ถูกแยกความจำเพาะออกเป็นฟันน้ำนม `6995000` และฟันแท้ `10679007` ข้างต้น)
   - `95217000`, `109540007`, `311341000009108`
3. **`Description Preference Change` (5 แถว):** เปลี่ยนคำหลัก (`Preferred`) ของ Concept เดิมให้เหมาะสมกับทางคลินิกยิ่งขึ้น
4. **`New Description` (21 แถว):** เพิ่มคำพ้อง (`Acceptable`) ใหม่ให้กับ Concept เดิม
5. **`Retired Description` (25 แถว):** ยกเลิกคำพ้องที่ล้าสมัย

---

## 3. รายการปรับปรุงสคริปต์ของระบบเพื่อรองรับการอัปเดตรุ่นใหม่

เพื่อให้การอัปเดตฐานข้อมูลสู่รุ่น `20260930` / `20261101` และการอัปเดตในรอบปีถัดๆ ไปทำงานได้อย่างราบรื่น 100% จึงมีแนวทางการปรับปรุงสคริปต์ 5 จุดดังนี้:

1. **การจัดโครงสร้างโฟลเดอร์ `sources/` และการค้นหาไฟล์ต้นฉบับ (`find_sources`):**
   - กำหนดให้ `d:\imnipon_project\kahis-terminology\sources\` (`1_SA-PDT`, `2_VSCT`, `3_SCT-Int`, `4_KU-Custom`) เป็นที่ตั้งหลักของไฟล์ต้นฉบับบน Localhost
   - ปรับ `get_search_roots()` ให้รองรับการค้นหาโฟลเดอร์ย่อยใน `~/Downloads` (เช่น `Download Terminology*`) และเรียงลำดับเลือกไฟล์ที่มีวันที่ (`YYYYMMDD`) ใหม่ที่สุดเสมอ
2. **การรองรับไฟล์ `.xml` ของ SA-PDT ควบคู่กับไฟล์ `.txt`:**
   - เพิ่มฟังก์ชันอ่านไฟล์ `ReleaseFile_full_*.xml` ใน `build_direct_db.py` เพื่อให้สามารถสร้าง DB ได้ทั้งจากไฟล์ `.txt` และจากไฟล์ `.xml` ที่แตกมาจาก `Full Release Package (.zip)`
3. **การนำข้อมูลจากไฟล์ Changes (`*to*`) มาเติมคอลัมน์ `sapdt_change_type`:**
   - อ่านไฟล์ `SA-PDTReleaseFile_*to*.txt` หรือ `ReleaseFile_*to*.xml` เพื่อนำค่า `CHANGETYPE` มาบันทึกในคอลัมน์ `sapdt_change_type` ของตาราง `terms`
4. **การฝังตาราง `db_metadata` และการสำเนาไฟล์ลงโฟลเดอร์ `releases/`:**
   - บันทึกเลขเวอร์ชันของทั้ง 3 แหล่ง (`SA-PDT 20260930`, `VSCT 20260930`, `SCT 20261101`) ลงในตาราง `db_metadata` ภายในไฟล์ SQLite เพื่อให้ทั้งหน้า Browser (เวลาโหลดไฟล์ `.db` จากเครื่อง) และหน้า Admin แสดงเลขเวอร์ชันตามไฟล์ฐานข้อมูลจริงโดยอัตโนมัติ
   - บันทึกสำเนาไฟล์ฐานข้อมูลที่สร้างเสร็จไว้ใน `releases/kahis_SAPDT<ver>_VSCT<ver>_SCT<ver>.db`
5. **การปรับ `scripts/verify_db.py` ให้ตรวจสอบจำนวนข้อมูลแบบ Dynamic Source Parity:**
   - เปลี่ยนจากการล็อกตัวเลขตายตัวของรุ่น `20260331` (`4,489` / `40,830`) เป็นการคำนวณจำนวน Concept ต้นทางจากไฟล์ใน `sources/` ของรุ่นที่กำลังสร้างมาเทียบกับจำนวนในตาราง `terms` แบบ 100% Dynamic Parity เพื่อให้ชุดตรวจ QA 34 จุดรองรับการอัปเดตทุกรุ่นในอนาคต
