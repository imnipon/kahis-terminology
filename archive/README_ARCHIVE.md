# โฟลเดอร์เก็บถาวร (Archive Directory) — KAHIS Terminology

โฟลเดอร์ `archive/` นี้ใช้เก็บรวบรวมไฟล์เอกสาร สคริปต์ และการตั้งค่ารุ่นเก่าที่ถูกทดแทนด้วยสถาปัตยกรรมใหม่ (v6.1) แล้ว เพื่อให้โครงสร้างหลักของโปรเจกต์สะอาดและชัดเจน โดยยังคงเก็บประวัติไฟล์เดิมไว้ครบถ้วน:

## 1. `archive/documents/` (เอกสารรุ่นเก่าที่ถูกสร้างทดแทนแล้ว)
- `audit_report_v5.md` ➔ ทดแทนด้วย `documents/KAHIS_3Sources_Priority_and_Field_Evolution.md` และ `documents/KAHIS_DB_Comparison_20260331_vs_20260930.md`
- `ku_synonyms_guide.md` ➔ ทดแทนด้วย `documents/KAHIS_Hybrid_Cloud_and_Local_Architecture_Guide.md`
- `lastcheck_20260721.md` ➔ ทดแทนด้วย `documents/KAHIS_DB_Comparison_20260331_vs_20260930.md`
- `logic_structure.md` ➔ ทดแทนด้วย `documents/KAHIS_3Sources_Priority_and_Field_Evolution.md` และ `documents/KAHIS_DB_Builder_Master_Spec_v6.md`
- `troubleshoot_01.md` ➔ บันทึกการแก้ปัญหารุ่น v4 เดิม

## 2. `archive/scripts/` (สคริปต์รุ่นเก่าที่ถูกควบรวมเข้า `build_direct_db.py` แล้ว)
- `build_search_db.py` ➔ สคริปต์สร้าง DB จาก CSV รุ่น v1–v4 (ทดแทนด้วย `scripts/build_direct_db.py` ที่อ่านจาก `sources/` โดยตรง)
- `build_body_system.py` ➔ สคริปต์คำนวณ Body System แยกต่างหากในรุ่น v4 (ปัจจุบันรวมอยู่ใน Step 4 ของ `scripts/build_direct_db.py` แล้ว)
- `seed_firestore.py` ➔ สคริปต์ทดสอบอัปโหลด DB ขึ้น Firestore ยุคก่อนเปลี่ยนมาใช้สถาปัตยกรรม Hybrid (SQLite Local + Firestore เฉพาะคำพ้องใหม่)

## 3. `archive/legacy_configs/`, `archive/legacy_data/`, `archive/static/`, `archive/backup/`
- `legacy_configs/supabase_setup.sql` ➔ ไฟล์ SQL สมัยทดสอบ Supabase (ปัจจุบันใช้ Firebase Firestore + SQLite)
- `legacy_data/ku_custom_synonyms.csv` ➔ ไฟล์คำพ้องรุ่นเดิมที่ไม่มีเลขเวอร์ชัน (ทดแทนด้วย `sources/4_KU-Custom/ku_synonym_text_20261106.csv`)
- `static/manual.html` ➔ หน้าคู่มือแยกต่างหากรุ่น v4 (ปัจจุบันรวมเป็น Modal คู่มือการใช้งานโทนสว่างใน `static/index.html` แล้ว)
- `backup/terminology_search_v4.db.gz` ➔ ไฟล์ฐานข้อมูลบีบอัดรุ่น v4 ดั้งเดิม
