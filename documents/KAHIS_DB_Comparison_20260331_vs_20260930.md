# รายงานเปรียบเทียบข้อมูลฐานข้อมูล KAHIS Terminology รุ่นเดิม (`20260331`) เทียบกับรุ่นใหม่ (`20260930 / 20261101`)

เอกสารฉบับนี้สรุปผลการเปรียบเทียบจำนวนรายการและการเปลี่ยนแปลงเชิงลึกของฐานข้อมูล **KAHIS Terminology (`terminology_search.db`)** ระหว่างรุ่นก่อนหน้าและรุ่นล่าสุดที่อยู่ในโฟลเดอร์ `releases/` ของโปรเจกต์

---

## 1. ข้อมูลรุ่นฐานข้อมูลที่เปรียบเทียบ (Release Metadata)

| รายการ | ฐานข้อมูลรุ่นเดิม (Old Release DB) | ฐานข้อมูลรุ่นใหม่ (New Release DB) |
| :--- | :--- | :--- |
| **ชื่อไฟล์ใน `releases/`** | `kahis_SAPDT20260331_VSCT20260331_SCT20260701_KU20260721.db` | `kahis_SAPDT20260930_VSCT20260930_SCT20261101_KU20261106.db` |
| **แหล่งที่ 1: SA-PDT** | `SA-PDT 20260331` (March 2026) | `SA-PDT 20260930` (September 2026) |
| **แหล่งที่ 2: VSCT** | `VSCT 20260331` (March 2026) | `VSCT 20260930` (September 2026) |
| **แหล่งที่ 3: SCT-Int** | `SCT 20260701` (July 2026) | `SCT 20261101` (November 2026) |
| **แหล่งที่ 4: KU Custom** | `KU 20260721` (190 รายการ) | `KU 20261106` (`ku_synonym_text_20261106.csv`, 190 รายการ) |
| **ขนาดไฟล์ `.db` / `.db.gz`** | 199.9 MB / 51.6 MB | **206.6 MB / 53.6 MB** |

---

## 2. ตารางเปรียบเทียบจำนวนรายการทั้งหมด (Statistical Summary)

| หมวดหมู่ / ตารางในฐานข้อมูล | รุ่นเดิม (`20260331`) | รุ่นใหม่ (`20260930 / 20261101`) | ส่วนต่าง (Diff) | คำอธิบาย |
| :--- | :---: | :---: | :---: | :--- |
| **1. ตาราง `terms` (มโนทัศน์สัตวแพทย์รวม `SA-PDT ∪ VSCT`)** | **42,299** | **42,347** | **+48** | จำนวน Concept สัตวแพทย์ทั้งหมดในระบบ |
| ├── สถานะ Active (`SA-PDT Active OR VSCT Active`) | 40,399 | **40,396** | -3 | มีการ Retire รหัสเก่าใน VSCT/SCT และแทนที่ด้วยรหัสใหม่ |
| ├── สถานะ Inactive / Retired | 1,900 | **1,951** | **+51** | เก็บรหัสที่ถูก Retire พร้อม `replacement_concept_id` |
| ├── **แหล่งที่ 1: SA-PDT ทั้งหมด (`in_sapdt='Yes'`)** | 4,489 | **4,492** | **+3** | เพิ่มรหัสใหม่ใน SA-PDT 3 รหัส |
| │   ├── SA-PDT Active (`sapdt_status='Active'`) | 4,103 | **4,103** | 0 | เพิ่มใหม่ 3 รหัส และปรับเป็น Retired 3 รหัสสุทธิเท่าเดิม |
| │   └── SA-PDT Retired (`sapdt_status='Retired'`) | 386 | **389** | **+3** | ปรับสถานะเป็น Retired เพื่อชี้ไปรหัสมาตรฐานใหม่ |
| ├── **แหล่งที่ 2: VSCT ทั้งหมด (`in_vsct='Yes'`)** | 40,830 | **40,879** | **+49** | เพิ่มรหัสสัตวแพทย์และสายพันธุ์สัตว์ใหม่ใน VSCT |
| ├── มีเฉพาะใน VSCT (`in_vsct='Yes' AND in_sapdt='No'`) | 37,810 | **37,855** | **+45** | รหัส VSCT Only |
| ├── มีทั้งใน SA-PDT และ VSCT (`in_sapdt='Yes' AND in_vsct='Yes'`) | 3,020 | **3,024** | **+4** | รหัสที่เชื่อมตรงระหว่าง SA-PDT และ VSCT |
| └── เชื่อมโยงกับ SNOMED CT สากล (`in_sct_inter='Yes'`) | 7,957 | **8,021** | **+64** | รหัสสัตวแพทย์ที่มีอยู่ในฐานข้อมูลการแพทย์สากล |
| **2. ตาราง `concept_terms` (Global FSNs ทั้งโลก)** | **561,646** | **574,677** | **+13,031** | ชื่อ FSN สากลสำหรับโหมดค้นหาขยายและแสดงชื่อ Hierarchy |
| **3. ตาราง `relationships` (ความสัมพันธ์ทั้งหมด)** | **1,334,088** | **1,386,153** | **+52,065** | เส้นความสัมพันธ์ `Is a` (Parents/Children) และ `Finding site` |
| **4. ตาราง `ku_synonym_text` (คำพ้องภาษาไทย มก.)** | **190** | **190** | **0 (ครบ 100%)** | รักษาข้อมูลคำพ้องภาษาไทยและคำย่อคลินิกครบทุกแถว |

---

## 3. รายละเอียดการเปลี่ยนแปลงใน SA-PDT (`20260331` ➔ `20260930` จำนวน 28 Concepts)

อ้างอิงจากไฟล์ `SA-PDTReleaseFile_20260331to20260930.txt` ซึ่งถูกนำเข้ามาบันทึกในคอลัมน์ `sapdt_change_type` ของตาราง `terms` มีการเปลี่ยนแปลงใน 28 Concepts แบ่งเป็น 3 กลุ่มดังนี้:

### 3.1 การแทนที่รหัสเดิมด้วยรหัสใหม่ใน SA-PDT (New Concept vs Retired Concept)
ในรอบกันยายน 2026 ทาง VTSL ได้ปรับปรุงรหัส 3 โรคสำคัญโดย **Retire รหัสเดิม** แล้ว **บรรจุรหัส SNOMED CT มาตรฐานใหม่ (`New Concept`)** เข้ามาแทนที่ (รวมถึง Retire รหัสซ้ำของ `Pseudophakia` อีก 1 รหัส):

| ลำดับ | รหัสใหม่ที่เพิ่มเข้า SA-PDT (`New Concept`) | ชื่อ Display Name (SA-PDT Preferred) | ชื่อ FSN | รหัสเดิมที่ถูกปรับเป็น `Retired Concept` |
| :---: | :--- | :--- | :--- | :--- |
| 1 | **`1386301009`** | **Failure of exfoliation of tooth due to absence of succedaneous tooth** | `Failure of exfoliation of tooth due to absence of succedaneous tooth (disorder)` | แทนที่รหัสเดิม `109540007` (*Persistent deciduous tooth, no permanent tooth*) |
| 2 | **`6995000`** | **Failure of lactation** | `Failure of lactation (disorder)` | แทนที่รหัสเดิม `311341000009108` (*Failure of lactation in non-human animal*) โดยดึงรหัส `6995000` ซึ่งเดิมมีเฉพาะใน VSCT/SCT ขึ้นมาเป็นรหัสหลักของ SA-PDT |
| 3 | **`10679007`** | **Giardiasis** | `Infection caused by Giardia duodenalis (disorder)` | แทนที่รหัสเดิม `58265007` (*Giardiasis*) |
| 4 | *(ใช้รหัส `309523001` ที่มีอยู่แล้ว)* | **Pseudophakia** | `Artificial lens present (finding)` | ยกเลิกรหัสซ้ำ `95217000` (*Pseudophakic intraocular lens present*) และย้ายคำพ้องมาไว้ที่รหัส `309523001` |

### 3.2 ตารางครบทั้ง 28 Concepts ที่มีการเปลี่ยนแปลงใน SA-PDT รอบ `20260331to20260930`

| ลำดับ | Concept ID | Display Name | FSN | สถานะ SA-PDT | ประเภทการเปลี่ยนแปลง (`sapdt_change_type`) |
| :---: | :--- | :--- | :--- | :---: | :--- |
| 1 | `1386301009` | Failure of exfoliation of tooth due to absence of succedaneous tooth | Failure of exfoliation of tooth due to absence of succedaneous tooth (disorder) | Active | `New Concept` |
| 2 | `6995000` | Failure of lactation | Failure of lactation (disorder) | Active | `New Concept` |
| 3 | `10679007` | Giardiasis | Infection caused by Giardia duodenalis (disorder) | Active | `New Concept` |
| 4 | `311341000009108` | Failure of lactation | Failure of lactation in non-human animal (disorder) | Retired | `Retired Concept` |
| 5 | `58265007` | Giardiasis | Giardiasis (disorder) | Retired | `Retired Concept` |
| 6 | `109540007` | Persistent deciduous tooth, no permanent tooth | Failure of exfoliation associated with lack of succedaneous tooth (disorder) | Retired | `Retired Concept` |
| 7 | `95217000` | Pseudophakia | Pseudophakic intraocular lens present (finding) | Retired | `Retired Concept` |
| 8 | `309523001` | Pseudophakia | Artificial lens present (finding) | Active | `New Description` |
| 9 | `1149327007` | Clostridium botulinum intoxication | Poisoning caused by Clostridium botulinum toxin (disorder) | Active | `New Description \| Description Preference Change \| Retired Description` |
| 10 | `109841003` | Liver cell carcinoma | Malignant hepatocellular carcinoma (disorder) | Active | `New Description \| Description Preference Change \| Retired Description` |
| 11 | `309971000009103` | Edema of quadruped foot | Edema of quadruped foot (finding) | Active | `Description Preference Change \| Retired Description` |
| 12 | `404037002` | Malignant peripheral nerve sheath tumor | Malignant peripheral nerve sheath tumor (disorder) | Active | `Description Preference Change \| Retired Description` |
| 13 | `309571000009106` | Plasmacytoma of animal | Plasmacytoma of animal (disorder) | Active | `Description Preference Change \| Retired Description` |
| 14 | `278040002` | Alopecia finding | Loss of hair (finding) | Active | `New Description \| Retired Description` |
| 15 | `128091003` | Autoimmune thrombocytopenia | Autoimmune thrombocytopenia (disorder) | Active | `New Description \| Retired Description` |
| 16 | `275671000009107` | Circling | Circling behavior (finding) | Active | `New Description \| Retired Description` |
| 17 | `356641000009104` | Congenital dynamic left ventricular outflow tract obstruction | Congenital dynamic left ventricular outflow tract obstruction (disorder) | Active | `New Description \| Retired Description` |
| 18 | `398565003` | Infection caused by Clostridium botulinum | Infection caused by Clostridium botulinum (disorder) | Active | `New Description \| Retired Description` |
| 19 | `414562003` | Knuckling | Knuckling over (finding) | Active | `New Description \| Retired Description` |
| 20 | `311151000009109` | Mastitis - non-human | Inflammation of non-human mammary gland (disorder) | Active | `New Description \| Retired Description` |
| 21 | `281811000009105` | Mixed pulmonary pattern | Abnormal pulmonary mixed radiographic pattern (finding) | Active | `New Description \| Retired Description` |
| 22 | `418697001` | Monocytosis finding | Blood monocyte number above reference range (finding) | Active | `New Description \| Retired Description` |
| 23 | `314561000009103` | Postitis | Inflammation of prepuce of animal (finding) | Active | `New Description \| Retired Description` |
| 24 | `93448009` | Skin erosion | Superficial ulcer of skin (disorder) | Active | `New Description \| Retired Description` |
| 25 | `34255001` | Superficial gingival ulcer | Superficial gingival ulcer (disorder) | Active | `New Description \| Retired Description` |
| 26 | `361521000009109` | Round cell tumor | Round cell tumor (disorder) | Active | `Retired Description` |
| 27 | `50792001` | Superficial corneal ulcer | Corneal erosion (disorder) | Active | `Retired Description` |
| 28 | `427537009` | Vulvar labium erosion | Erosion of vulvar labia (disorder) | Active | `Retired Description` |

---

## 4. รายชื่อครบทั้ง 48 Concepts ใหม่ที่เพิ่มเข้ามาในตาราง `terms` (`42,299` ➔ `42,347`)

ตารางด้านล่างแสดงรหัสใหม่ทั้ง **48 Concepts** ที่ไม่เคยมีในฐานข้อมูลรุ่น `20260331` และถูกเพิ่มเข้ามาในรุ่น `20260930 / 20261101` (ประกอบด้วยโรคทางคลินิก การตรวจทางห้องปฏิบัติการ ตัวอย่างส่งตรวจ และสายพันธุ์สัตว์ใน VSCT):

| ลำดับ | Concept ID | Display Name | FSN (`snomed_fsn`) | หมวดหมู่ (`Semantic Tag`) | SA-PDT | VSCT | SCT-Int |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| 1 | `1386301009` | Failure of exfoliation of tooth due to absence of succedaneous tooth | Failure of exfoliation of tooth due to absence of succedaneous tooth (disorder) | `disorder` | Yes | No | Yes |
| 2 | `10679007` | Giardiasis | Infection caused by Giardia duodenalis (disorder) | `disorder` | Yes | No | Yes |
| 3 | `2061091000009104` | Interdigital furunculosis | Interdigital furunculosis (disorder) | `disorder` | No | Yes | No |
| 4 | `2061101000009109` | Canine interdigital palmar and plantar comedones and follicular cysts | Canine interdigital palmar and plantar comedones and follicular cysts (disorder) | `disorder` | No | Yes | No |
| 5 | `836475004` | Mucopurulent nasal discharge | Mucopurulent discharge from nose (finding) | `finding` | No | Yes | Yes |
| 6 | `2061081000009101` | Urine cystatin B measurement | Measurement of cystatin B in urine (procedure) | `procedure` | No | Yes | No |
| 7 | `2061071000009103` | Cystatin B | Cystatin B (substance) | `substance` | No | Yes | No |
| 8 | `2041421000009100` | Formalin-fixed paraffin-embedded tissue scroll specimen | Formalin-fixed paraffin-embedded tissue scroll specimen (specimen) | `specimen` | No | Yes | No |
| 9 | `2051071000009109` | Swab of avian crop | Swab of avian crop (specimen) | `specimen` | No | Yes | No |
| 10 | `818996002` | Structure of subcutaneous vein of abdomen | Structure of subcutaneous vein of abdomen (body structure) | `body structure` | No | Yes | Yes |
| 11 | `2041381000009106` | Lykoi cat breed | Lykoi cat breed (organism) | `organism` | No | Yes | No |
| 12 | `2051091000009108` | Indian Pariah Dog breed | Indian Pariah Dog breed (organism) | `organism` | No | Yes | No |
| 13 | `2051101000009103` | Kanni dog | Kanni dog breed (organism) | `organism` | No | Yes | No |
| 14 | `2051111000009101` | Mudhol Hound | Mudhol Hound dog breed (organism) | `organism` | No | Yes | No |
| 15 | `2051121000009109` | Kombai dog | Kombai dog breed (organism) | `organism` | No | Yes | No |
| 16 | `2051131000009106` | Rajapalayam dog | Rajapalayam dog breed (organism) | `organism` | No | Yes | No |
| 17 | `2051141000009100` | Bakharwal dog | Bakharwal dog breed (organism) | `organism` | No | Yes | No |
| 18 | `2051151000009102` | Rampur Greyhound | Rampur Greyhound dog breed (organism) | `organism` | No | Yes | No |
| 19 | `2051161000009104` | Chippiparai dog | Chippiparai dog breed (organism) | `organism` | No | Yes | No |
| 20 | `131633002` | Peacock Goat breed | Peacock Goat breed (organism) | `organism` | No | Yes | Yes |
| 21 | `2051081000009106` | Valais Blacknose sheep breed | Valais Blacknose sheep breed (organism) | `organism` | No | Yes | No |
| 22 | `2041391000009108` | Dutch Riding Pony breed | Dutch Riding Pony breed (organism) | `organism` | No | Yes | No |
| 23 | `2041401000009106` | Genus Neogale | Genus Neogale (organism) | `organism` | No | Yes | No |
| 24 | `2041411000009108` | Genus Lophotriorchis | Genus Lophotriorchis (organism) | `organism` | No | Yes | No |
| 25 | `2041301000009104` | Callichthyidae | Family Callichthyidae (organism) | `organism` | No | Yes | No |
| 26 | `2041311000009102` | Corydoradinae | Subfamily Corydoradinae (organism) | `organism` | No | Yes | No |
| 27 | `2041321000009105` | Corydoras | Genus Corydoras (organism) | `organism` | No | Yes | No |
| 28 | `2041331000009107` | Corydoras davidsandsi | Corydoras davidsandsi (organism) | `organism` | No | Yes | No |
| 29 | `2041431000009103` | Xiphophorus hellerii Alpha base color red | Xiphophorus hellerii Alpha base color red (organism) | `organism` | No | Yes | No |
| 30 | `84316004` | Red shiner | Notropis lutrensis (organism) | `organism` | No | Yes | Yes |
| 31 | `449256002` | Galapagos giant tortoise | Geochelone nigra (organism) | `organism` | No | Yes | Yes |
| 32 | `2041341000009101` | Rallus obsoletus | Rallus obsoletus (organism) | `organism` | No | Yes | No |
| 33 | `2041351000009103` | Rallus crepitans | Rallus crepitans (organism) | `organism` | No | Yes | No |
| 34 | `2041361000009100` | Rallus crepitans caribaeus | Rallus crepitans caribaeus (organism) | `organism` | No | Yes | No |
| 35 | `2041371000009109` | Rallus crepitans pallidus | Rallus crepitans pallidus (organism) | `organism` | No | Yes | No |
| 36 | `112510004` | Blue-footed booby | Blue-footed booby (organism) | `organism` | No | Yes | Yes |
| 37 | `112520009` | Kittiwake | Kittiwake (organism) | `organism` | No | Yes | Yes |
| 38 | `1751004` | Golden-crowned kinglet | Golden-crowned kinglet (organism) | `organism` | No | Yes | Yes |
| 39 | `26571005` | Luzon hornbill | Luzon hornbill (organism) | `organism` | No | Yes | Yes |
| 40 | `27688002` | Setophaga ruticilla | American redstart (organism) | `organism` | No | Yes | Yes |
| 41 | `31792003` | Maleo | Maleo (organism) | `organism` | No | Yes | Yes |
| 42 | `39735001` | Procnias tricarunculatus | Three-wattled bellbird (organism) | `organism` | No | Yes | Yes |
| 43 | `46712001` | Ruby-crowned kinglet | Ruby-crowned kinglet (organism) | `organism` | No | Yes | Yes |
| 44 | `57394000` | Tooth-billed bowerbird | Tooth-billed catbird (organism) | `organism` | No | Yes | Yes |
| 45 | `63827005` | Sayornis phoebe | Eastern phoebe (organism) | `organism` | No | Yes | Yes |
| 46 | `65309000` | Setophaga virens | Black-throated green warbler (organism) | `organism` | No | Yes | Yes |
| 47 | `6721009` | Yellow-billed cuckoo | Yellow-billed cuckoo (organism) | `organism` | No | Yes | Yes |
| 48 | `82238003` | Egyptian plover | Egyptian plover (organism) | `organism` | No | Yes | Yes |
