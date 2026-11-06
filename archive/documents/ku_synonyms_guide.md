# KU Custom Synonyms — แนวทางการจัดการและ Update

**เอกสาร:** KAHIS Terminology  
**เวอร์ชัน:** 1.0 (2026-07-21)

---

## 1. KU Synonym คืออะไร?

KU Synonym คือ term ภาษาไทย หรือ term เฉพาะที่ทีม KU กำหนดขึ้นเอง สำหรับ SNOMED CT concept ที่ **ไม่มีใน SA-PDT, VSCT, หรือ SCT-International**

ตัวอย่างปัจจุบัน (`ku_custom_synonyms.csv`):

| concept_id | display_name | ku_synonym_text | lang_tag |
|---|---|---|---|
| 11833005 | Dry cough | ไอแห้ง | ku |
| 49727002 | Cough | ไอแห้ง | ku |

---

## 2. ที่เก็บข้อมูล (Source of Truth)

```
kahis-terminology/output/ku_custom_synonyms.csv
```

ไฟล์นี้ **อยู่นอก App directory** และ **ไม่ถูก gitignore** → ปลอดภัย ไม่หายเมื่อ Rebuild DB

---

## 3. สิ่งที่ยังขาด — Integration กับ Build Pipeline

ปัจจุบัน `build_direct_db.py` **ยังไม่ได้** อ่าน `ku_custom_synonyms.csv` เข้า DB

### ผลที่เกิดขึ้น:
- KU synonyms อยู่ใน CSV เท่านั้น
- ไม่ถูก index ใน FTS (Full Text Search)
- ไม่แสดงใน search results ของ UI

### สิ่งที่ต้องเพิ่มใน `build_direct_db.py` (TODO):

```python
# Step 6.5: Load KU custom synonyms
KU_SYNONYMS_PATH = os.path.join(KAHIS_DIR, 'output', 'ku_custom_synonyms.csv')

def load_ku_synonyms(path):
    """อ่าน KU custom synonyms จาก CSV และ merge เข้า terms"""
    if not os.path.exists(path):
        log(f'KU synonyms not found: {path}', 'WARN')
        return {}
    ku_map = {}  # concept_id -> [ku_synonym_text, ...]
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            cid = row['concept_id'].strip()
            syn = row['ku_synonym_text'].strip()
            if cid and syn:
                ku_map.setdefault(cid, []).append(syn)
    log(f'KU synonyms loaded: {len(ku_map)} concepts')
    return ku_map

# ใน main():
ku_synonyms = load_ku_synonyms(KU_SYNONYMS_PATH)

# เมื่อเขียน DB — เพิ่ม ku_synonyms ใน snomed_all_synonyms
for rec in sapdt.values():
    cid = rec['snomed_concept_id']
    ku_syns = ku_synonyms.get(cid, [])
    if ku_syns:
        existing = rec.get('snomed_all_synonyms', '')
        rec['snomed_all_synonyms'] = ' | '.join(
            filter(None, [existing] + ku_syns)
        )
        rec['has_ku_synonym'] = 'Yes'
```

---

## 4. Workflow เมื่อ Release ใหม่ (SA-PDT / VSCT / SCT-Int)

### กรณีปกติ — Source ออก Release ใหม่

```
ก่อน Rebuild
└── ✅ Backup DB ก่อน
    cp terminology_search.db backup/terminology_search_YYYYMMDD_HHMMSS.db.gz

วางไฟล์ Release ใหม่
├── SA-PDT:   วาง folder ใหม่แทน SA-PDT-Terminology-MMDD-YYYY/
├── VSCT:     วาง folder ใหม่แทน SnomedCT_VETExtension_*/
└── SCT-Int:  วาง folder ใหม่แทน SnomedCT_InternationalRF2_*/

⚠️  สำคัญ: ลบหรือย้าย release เก่าออกก่อน!
    (find_rf2() ใช้ glob — ถ้ามีหลาย folder อาจโหลดผิดไฟล์)

ปรับ path ใน server.py (ถ้าชื่อ folder เปลี่ยน)
└── SAPDT_DIR, VSCT_DIR, SCT_DIR

Rebuild DB
└── python3 scripts/build_direct_db.py
    หรือ กด Rebuild ใน admin.html

รัน Health Check
└── ดู SQL Q1-Q5 ใน documents/troubleshoot_01.md

KU Synonyms (ยังคงอยู่ใน CSV — ไม่ต้องทำอะไรเพิ่ม)
└── output/ku_custom_synonyms.csv ไม่ถูกแตะต้อง
```

---

## 5. ตารางเปรียบเทียบ — สิ่งที่หายและไม่หายเมื่อ Rebuild

| ข้อมูล | เก็บที่ | หายเมื่อ Rebuild? | หมายเหตุ |
|---|---|---|---|
| SNOMED terms/FSN | DB | ✅ Rebuild ใหม่ | ได้จาก source files |
| Relationships | DB | ✅ Rebuild ใหม่ | ได้จาก source files |
| KU Synonyms | CSV | ❌ ไม่หาย | อยู่นอก DB |
| Backup DB | `backup/` | ❌ ไม่หาย | gitignore แต่ยังอยู่ local |
| Documents/MD | `documents/` | ❌ ไม่หาย | tracked ใน git |

---

## 6. แนวทางเพิ่ม KU Synonym ใหม่

1. เปิดไฟล์ `../output/ku_custom_synonyms.csv`
2. เพิ่มแถวใหม่:
   ```csv
   3,<concept_id>,<display_name>,<snomed_fsn>,<thai_term>,ku,<datetime>
   ```
3. Rebuild DB (เมื่อ integration พร้อม จะถูก index อัตโนมัติ)

---

## 7. Backup Strategy

| เมื่อใด | คำสั่ง |
|---|---|
| ก่อน Rebuild ทุกครั้ง | `gzip -9 -k -f terminology_search.db` แล้ว copy พร้อม datetime |
| ก่อน Update release | Backup ก่อนเสมอ |
| Production deploy | ใช้ `backup/terminology_search_YYYYMMDD_HHMMSS.db.gz` |

> ✅ การ Backup = การดึง DB เก็บไว้เป็น gz **ถูกต้องแล้ว**
> เพราะ DB คือ source of truth ที่ rebuild ได้ แต่ใช้เวลา
> gz ลดขนาดจาก 204 MB → 51 MB (~75% compression)
