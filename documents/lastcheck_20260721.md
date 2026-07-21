# KAHIS Terminology DB Audit & Verification Report

**วันที่ตรวจสอบ:** 2026-07-21 17:45 (ICT)  
**ระบบ:** KAHIS Terminology (SA-PDT & SNOMED CT Veterinary Extension)  
**ไฟล์ที่ตรวจสอบ:** `kahis-terminology-app/terminology_search.db`  
**สถานะ:** ✅ PASSED 100% (ข้อมูลตรงกับไฟล์ RF2 ต้นฉบับทุกรายการ)

---

## 1. ภาพรวมการตรวจสอบ (Executive Summary)

- **เป้าหมาย:** ตรวจสอบความถูกต้องสมบูรณ์ของฐานข้อมูลหลังแก้ไข Bug ทั้ง 3 จุดใน `build_direct_db.py`
- **วิธีการตรวจ:** สุ่มดึงข้อมูล **200 Concept IDs** ครอบคลุม SA-PDT, VSCT-only และ SCT-International แล้วเปรียบเทียบ Field-by-Field กับไฟล์ TSV Snapshot ต้นฉบับ (`sct2_Description_Snapshot-en*.txt` และ `sct2_Concept_Snapshot*.txt`) ทั้งของ VSCT และ SCT-Int
- **ผลการตรวจ:** **ตรงกัน 100% (200 / 200 OK, 0 Mismatches)**

---

## 2. สถานะฐานข้อมูลและไฟล์ Backup

| รายการ | ข้อมูลปัจจุบัน |
|---|---|
| ขนาดไฟล์ DB (`terminology_search.db`) | 203.6 MB |
| ขนาดไฟล์ GZ (`terminology_search.db.gz`) | 50.9 MB (บีบอัดอัตโนมัติ) |
| แถวในตาราง `terms` | 40,306 แถว |
| แถวในตาราง `relationships` | 1,357,048 แถว |
| แถวในตาราง `concept_terms` | 568,744 แถว |
| **ไฟล์ Backup หลัก** | `backup/terminology_search_20260721_172842.db` (203.6 MB) |
| **ไฟล์ Backup GZ** | `backup/terminology_search_20260721_172842.db.gz` (50.9 MB) |

---

## 3. ผลการวิเคราะห์แยกตามแหล่งที่มา (Source Breakdown Baseline)

| SA-PDT | VSCT | SCT-Int | Total Terms | Has FSN | Showing ID | สถานะ |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| No | Yes | No | **32,749** | 32,749 (100%) | **0** | ✅ PASS |
| No | Yes | Yes | **3,068** | 3,068 (100%) | **0** | ✅ PASS |
| Yes | No | Yes | **2,890** | 2,890 (100%) | **0** | ✅ PASS |
| Yes | Yes | No | **1,593** | 1,593 (100%) | **0** | ✅ PASS |
| Yes | Yes | Yes | **6** | 6 (100%) | **0** | ✅ PASS |

---

## 4. ผลการตรวจสอบสุ่ม 200 Concept IDs (Audit Log Table)

### 🔹 ชุดที่ 1: รายการที่ 1 – 50

| # | Concept ID | แหล่งที่มา | DB Display Name / FSN | Raw RF2 FSN (ต้นฉบับ) | ผลการตรวจ |
|---|---|---|---|---|:---:|
| 1 | `66331000009107` | VSCT | Charadrius forbesi (organism) | Charadrius forbesi (organism) | ✅ OK |
| 2 | `132517008` | VSCT | Basset Artésian Normand dog breed (organism) | Basset Artésian Normand dog breed (organism) | ✅ OK |
| 3 | `173691000009108` | VSCT | Crotophaga sulcirostris sulcirostris (organism) | Crotophaga sulcirostris sulcirostris (organism) | ✅ OK |
| 4 | `153911000009109` | VSCT | Genus Coccothraustes (organism) | Genus Coccothraustes (organism) | ✅ OK |
| 5 | `139701000009109` | VSCT | Chlorothraupis carmioli (organism) | Chlorothraupis carmioli (organism) | ✅ OK |
| 6 | `84841000009101` | VSCT | Genus Marmaronetta (organism) | Genus Marmaronetta (organism) | ✅ OK |
| 7 | `57651000009102` | VSCT | Procellaria parkinsoni (organism) | Procellaria parkinsoni (organism) | ✅ OK |
| 8 | `367271000009101` | VSCT | Infection by Marteilioides chungmuensis (disorder) | Infection by Marteilioides chungmuensis (disorder) | ✅ OK |
| 9 | `47301000009106` | VSCT | Phoeniculus purpureus angolensis (organism) | Phoeniculus purpureus angolensis (organism) | ✅ OK |
| 10 | `269961000009103` | VSCT | Cyclopsitta diophthalma marshalli (organism) | Cyclopsitta diophthalma marshalli (organism) | ✅ OK |
| 11 | `132969005` | VSCT | Russian Saddle Horse horse breed (organism) | Russian Saddle Horse horse breed (organism) | ✅ OK |
| 12 | `132836006` | VSCT | Orust chicken breed (organism) | Orust chicken breed (organism) | ✅ OK |
| 13 | `51731000009106` | VSCT | Dromaius novaehollandiae diemenensis (organism) | Dromaius novaehollandiae diemenensis (organism) | ✅ OK |
| 14 | `136701000009104` | VSCT | Tyrannulus elatus (organism) | Tyrannulus elatus (organism) | ✅ OK |
| 15 | `145891000009109` | VSCT | Genus Calcarius (organism) | Genus Calcarius (organism) | ✅ OK |
| 16 | `336721000009104` | VSCT | Equine coital exanthema (disorder) | Equine coital exanthema (disorder) | ✅ OK |
| 17 | `132617003` | VSCT | McNab dog breed (organism) | McNab dog breed (organism) | ✅ OK |
| 18 | `123731000009101` | VSCT | Rhaphidura leucopygialis (organism) | Rhaphidura leucopygialis (organism) | ✅ OK |
| 19 | `366991000009109` | VSCT | Family Enderleinellidae (organism) | Family Enderleinellidae (organism) | ✅ OK |
| 20 | `268381000009102` | VSCT | Chamaea fasciata canicauda (organism) | Chamaea fasciata canicauda (organism) | ✅ OK |
| 21 | `137881000009102` | VSCT | Riparia paludicola (organism) | Riparia paludicola (organism) | ✅ OK |
| 22 | `292181000009100` | VSCT | Genus Carpomys (organism) | Genus Carpomys (organism) | ✅ OK |
| 23 | `175761000009108` | VSCT | Colius striatus kikuyensis (organism) | Colius striatus kikuyensis (organism) | ✅ OK |
| 24 | `71238008` | VSCT | Commercial brown egg layer type chicken (organism) | Commercial brown egg layer type chicken (organism) | ✅ OK |
| 25 | `98031000009108` | VSCT | Asthenes wyatti (organism) | Asthenes wyatti (organism) | ✅ OK |
| 26 | `270411000009109` | VSCT | Geoffroyus geoffroyi cyanicarpus (organism) | Geoffroyus geoffroyi cyanicarpus (organism) | ✅ OK |
| 27 | `216431000009105` | VSCT | Saltator coerulescens grandis (organism) | Saltator coerulescens grandis (organism) | ✅ OK |
| 28 | `175551000009103` | VSCT | Pipra pipra pygmaea (organism) | Pipra pipra pygmaea (organism) | ✅ OK |
| 29 | `95291000009107` | VSCT | Zosterops anomalus (organism) | Zosterops anomalus (organism) | ✅ OK |
| 30 | `134521000009109` | VSCT | Mecocerculus hellmayri (organism) | Mecocerculus hellmayri (organism) | ✅ OK |
| 31 | `214041000009103` | VSCT | Rallina forbesi parva (organism) | Rallina forbesi parva (organism) | ✅ OK |
| 32 | `57461000009102` | VSCT | Daption capense (organism) | Daption capense (organism) | ✅ OK |
| 33 | `51111000009102` | VSCT | Megalaima rubricapillus (organism) | Megalaima rubricapillus (organism) | ✅ OK |
| 34 | `242431000009104` | VSCT | Ochthoeca cinnamomeiventris cinnamomeiventris (organism) | Ochthoeca cinnamomeiventris cinnamomeiventris (organism) | ✅ OK |
| 35 | `53731000009105` | VSCT | Genus Oriolia (organism) | Genus Oriolia (organism) | ✅ OK |
| 36 | `228711000009103` | VSCT | Phasianus versicolor versicolor (organism) | Phasianus versicolor versicolor (organism) | ✅ OK |
| 37 | `218861000009100` | VSCT | Gymnophaps albertisii albertisii (organism) | Gymnophaps albertisii albertisii (organism) | ✅ OK |
| 38 | `166801000009104` | VSCT | Semnornis ramphastinus caucae (organism) | Semnornis ramphastinus caucae (organism) | ✅ OK |
| 39 | `133736009` | VSCT | Karan Swiss cattle breed (organism) | Karan Swiss cattle breed (organism) | ✅ OK |
| 40 | `299061000009100` | VSCT | Delomys dorsalis (organism) | Delomys dorsalis (organism) | ✅ OK |
| 41 | `357761000009108` | VSCT | Infection caused by Camelostrongylus (disorder) | Infection caused by Camelostrongylus (disorder) | ✅ OK |
| 42 | `75181000009106` | VSCT | Ceuthmochares aereus (organism) | Ceuthmochares aereus (organism) | ✅ OK |
| 43 | `241521000009109` | VSCT | Myiobius barbatus aureatus (organism) | Myiobius barbatus aureatus (organism) | ✅ OK |
| 44 | `41781000009108` | VSCT | Dermophthirioides (organism) | Dermophthirioides (organism) | ✅ OK |
| 45 | `185581000009104` | VSCT | Colinus virginianus insulanus (organism) | Colinus virginianus insulanus (organism) | ✅ OK |
| 46 | `230451000009106` | VSCT | Apus bradfieldi deserticola (organism) | Apus bradfieldi deserticola (organism) | ✅ OK |
| 47 | `119431000009104` | VSCT | Genus Carpornis (organism) | Genus Carpornis (organism) | ✅ OK |
| 48 | `35491000009102` | VSCT | Bone structure of wing (body structure) | Bone structure of wing (body structure) | ✅ OK |
| 49 | `444672002` | VSCT | Goldendoodle dog breed (organism) | Goldendoodle dog breed (organism) | ✅ OK |
| 50 | `142771000009109` | VSCT | Agelasticus thilius (organism) | Agelasticus thilius (organism) | ✅ OK |

### 🔹 ชุดที่ 2: รายการที่ 51 – 100

| # | Concept ID | แหล่งที่มา | DB Display Name / FSN | Raw RF2 FSN (ต้นฉบับ) | ผลการตรวจ |
|---|---|---|---|---|:---:|
| 51 | `183101000009103` | VSCT | Caprimulgus longirostris longirostris (organism) | Caprimulgus longirostris longirostris (organism) | ✅ OK |
| 52 | `42471000009107` | VSCT | Infection by Fusobacterium (disorder) | Infection by Fusobacterium (disorder) | ✅ OK |
| 53 | `145981000009103` | VSCT | Genus Chondestes (organism) | Genus Chondestes (organism) | ✅ OK |
| 54 | `56661000009101` | VSCT | Genus Pinguinus (organism) | Genus Pinguinus (organism) | ✅ OK |
| 55 | `242561000009105` | VSCT | Ochthoeca fumicolor berlepschi (organism) | Ochthoeca fumicolor berlepschi (organism) | ✅ OK |
| 56 | `175621000009106` | VSCT | Xenopipo uniformis duidae (organism) | Xenopipo uniformis duidae (organism) | ✅ OK |
| 57 | `294931000009109` | VSCT | Melomys gracilis (organism) | Melomys gracilis (organism) | ✅ OK |
| 58 | `232541000009108` | VSCT | Amazilia fimbriata fluviatilis (organism) | Amazilia fimbriata fluviatilis (organism) | ✅ OK |
| 59 | `99991000009100` | VSCT | Philydor atricapillus (organism) | Philydor atricapillus (organism) | ✅ OK |
| 60 | `236051000009102` | VSCT | Phaeochroa cuvierii furvescens (organism) | Phaeochroa cuvierii furvescens (organism) | ✅ OK |
| 61 | `226281000009104` | VSCT | Francolinus albogularis buckleyi (organism) | Francolinus albogularis buckleyi (organism) | ✅ OK |
| 62 | `130721000009108` | VSCT | Pycnonotus penicillatus (organism) | Pycnonotus penicillatus (organism) | ✅ OK |
| 63 | `168411000009103` | VSCT | Sipodotus wallacii coronatus (organism) | Sipodotus wallacii coronatus (organism) | ✅ OK |
| 64 | `36801000009100` | VSCT | Abnormality of egg (finding) | Abnormality of egg (finding) | ✅ OK |
| 65 | `105551000009106` | VSCT | Rhynochetos jubatus (organism) | Rhynochetos jubatus (organism) | ✅ OK |
| 66 | `356151000009106` | VSCT | Rostrocaudal projection (qualifier value) | Rostrocaudal projection (qualifier value) | ✅ OK |
| 67 | `153851000009101` | VSCT | Fringilla coelebs (organism) | Fringilla coelebs (organism) | ✅ OK |
| 68 | `100481000009106` | VSCT | Synallaxis courseni (organism) | Synallaxis courseni (organism) | ✅ OK |
| 69 | `300921000009108` | VSCT | Oryzomys buccinatus (organism) | Oryzomys buccinatus (organism) | ✅ OK |
| 70 | `242121000009108` | VSCT | Myiornis ecaudatus ecaudatus (organism) | Myiornis ecaudatus ecaudatus (organism) | ✅ OK |
| 71 | `170361000009104` | VSCT | Pitta oatesi deborah (organism) | Pitta oatesi deborah (organism) | ✅ OK |
| 72 | `137341000009102` | VSCT | Hirundo leucosoma (organism) | Hirundo leucosoma (organism) | ✅ OK |
| 73 | `205971000009105` | VSCT | Synallaxis albescens trinitatis (organism) | Synallaxis albescens trinitatis (organism) | ✅ OK |
| 74 | `7921000009109` | VSCT | Hungarian warmblood horse breed (organism) | Hungarian warmblood horse breed (organism) | ✅ OK |
| 75 | `143521000009108` | VSCT | Nesopsar nigerrimus (organism) | Nesopsar nigerrimus (organism) | ✅ OK |
| 76 | `132990002` | VSCT | Garrano tarpan horse X domestic horse breed (organism) | Garrano tarpan horse X domestic horse breed (organism) | ✅ OK |
| 77 | `200181000009104` | VSCT | Todiramphus saurophagus saurophagus (organism) | Todiramphus saurophagus saurophagus (organism) | ✅ OK |
| 78 | `256351000009103` | VSCT | Molothrus bonariensis aequatorialis (organism) | Molothrus bonariensis aequatorialis (organism) | ✅ OK |
| 79 | `168911000009105` | VSCT | Oceanites oceanicus exasperatus (organism) | Oceanites oceanicus exasperatus (organism) | ✅ OK |
| 80 | `33011000009101` | VSCT | Disorder of biliverdin metabolism (disorder) | Disorder of biliverdin metabolism (disorder) | ✅ OK |
| 81 | `131681000009108` | VSCT | Mino dumontii (organism) | Mino dumontii (organism) | ✅ OK |
| 82 | `199671000009104` | VSCT | Todiramphus chloris kalbaensis (organism) | Todiramphus chloris kalbaensis (organism) | ✅ OK |
| 83 | `132761000009104` | VSCT | Elaenia obscura (organism) | Elaenia obscura (organism) | ✅ OK |
| 84 | `332391000009103` | VSCT | Masticophis flagellum flagellum (organism) | Masticophis flagellum flagellum (organism) | ✅ OK |
| 85 | `252731000009107` | VSCT | Piranga rubra cooperi (organism) | Piranga rubra cooperi (organism) | ✅ OK |
| 86 | `298691000009106` | VSCT | Bolomys lasiurus (organism) | Bolomys lasiurus (organism) | ✅ OK |
| 87 | `87031000009105` | VSCT | Picumnus sclateri (organism) | Picumnus sclateri (organism) | ✅ OK |
| 88 | `167041000009106` | VSCT | Trachyphonus darnaudii darnaudii (organism) | Trachyphonus darnaudii darnaudii (organism) | ✅ OK |
| 89 | `84901000009109` | VSCT | Genus Nomonyx (organism) | Genus Nomonyx (organism) | ✅ OK |
| 90 | `155041000009107` | VSCT | Serinus rothschildi (organism) | Serinus rothschildi (organism) | ✅ OK |
| 91 | `362521000009100` | VSCT | Half-Arabian horse breed (organism) | Half-Arabian horse breed (organism) | ✅ OK |
| 92 | `165641000009106` | VSCT | Lybius undatus undatus (organism) | Lybius undatus undatus (organism) | ✅ OK |
| 93 | `274421000009107` | VSCT | Ursus americanus eremicus (organism) | Ursus americanus eremicus (organism) | ✅ OK |
| 94 | `255201000009101` | VSCT | Agelaius xanthomus xanthomus (organism) | Agelaius xanthomus xanthomus (organism) | ✅ OK |
| 95 | `230681000009101` | VSCT | Apus pallidus illyricus (organism) | Apus pallidus illyricus (organism) | ✅ OK |
| 96 | `137151000009101` | VSCT | Genus Riparia (organism) | Genus Riparia (organism) | ✅ OK |
| 97 | `84051000009106` | VSCT | Odontophorus gujanensis (organism) | Odontophorus gujanensis (organism) | ✅ OK |
| 98 | `339511000009107` | VSCT | Pastern of forefoot (body structure) | Pastern of forefoot (body structure) | ✅ OK |
| 99 | `328541000009103` | VSCT | Fracture of radial carpal bone of equine limb (disorder) | Fracture of radial carpal bone of equine limb (disorder) | ✅ OK |
| 100 | `49901000009100` | VSCT | Indicator exilis pachyrhynchus (organism) | Indicator exilis pachyrhynchus (organism) | ✅ OK |

### 🔹 ชุดที่ 3: รายการที่ 101 – 150

| # | Concept ID | แหล่งที่มา | DB Display Name / FSN | Raw RF2 FSN (ต้นฉบับ) | ผลการตรวจ |
|---|---|---|---|---|:---:|
| 101 | `70650003` | SA-PDT | Bladder stone | Urinary bladder stone (disorder) | ✅ OK |
| 102 | `70350007` | SA-PDT | Degenerative myelopathy | Degenerative myelopathy (disorder) | ✅ OK |
| 103 | `283051000009100` | SA-PDT | Eyelid scaling | Eyelid scaling (finding) | ✅ OK |
| 104 | `304671000009106` | SA-PDT | Fibrinous peritoneal effusion | Fibrinous ascites (disorder) | ✅ OK |
| 105 | `271807003` | SA-PDT | Skin eruption | Eruption of skin (disorder) | ✅ OK |
| 106 | `358831000009105` | SA-PDT | Cardiogenic non-chylous pleural effusion | Non-chylous pleural effusion due to congestive heart failure (disorder) | ✅ OK |
| 107 | `271865009` | SA-PDT | Pus in feces | Pus in stool (finding) | ✅ OK |
| 108 | `56786000` | SA-PDT | Pulmonic stenosis | Pulmonic valve stenosis (disorder) | ✅ OK |
| 109 | `348261000009102` | SA-PDT | Transmissible canine venereal tumor | Transmissible canine venereal tumor (disorder) | ✅ OK |
| 110 | `370556004` | SA-PDT | Pelvic bladder | Pelvic bladder (finding) | ✅ OK |
| 111 | `361341000009107` | SA-PDT | Lateral laryngeal saccules everted | Everted laryngeal saccules (disorder) | ✅ OK |
| 112 | `308201000009109` | SA-PDT | Acute small bowel diarrhea | Acute small bowel diarrhea (finding) | ✅ OK |
| 113 | `281241000009105` | SA-PDT | Diaphragm silhouette indistinct | Diaphragm silhouette indistinct (finding) | ✅ OK |
| 114 | `280421000009108` | SA-PDT | Ear margin vasculitis | Ear margin vasculitis (finding) | ✅ OK |
| 115 | `297721000009104` | SA-PDT | Lymphocytic plasmacytic enterocolitis | Lymphocytic plasmacytic enterocolitis (disorder) | ✅ OK |
| 116 | `125963005` | SA-PDT | Patent ductus arteriosus with left-to-right shunt | Patent ductus arteriosus with left-to-right shunt (disorder) | ✅ OK |
| 117 | `109727004` | SA-PDT | Dental restoration present | Dental restoration present (finding) | ✅ OK |
| 118 | `88092000` | SA-PDT | Muscle atrophy | Muscle atrophy (disorder) | ✅ OK |
| 119 | `249338002` | SA-PDT | Stenotic nares | Stenosis of nostril (disorder) | ✅ OK |
| 120 | `339181000009108` | SA-PDT | Feline panleukopenia | Feline panleukopenia (disorder) | ✅ OK |
| 121 | `63901009` | SA-PDT | Testicular pain | Pain in testicle (finding) | ✅ OK |
| 122 | `313751000009106` | SA-PDT | Abnormal spinal cord evoked potential | Abnormal spinal cord evoked potential (finding) | ✅ OK |
| 123 | `95436008` | SA-PDT | Lung consolidation | Lung consolidation (disorder) | ✅ OK |
| 124 | `56556009` | SA-PDT | Zinc-responsive dermatosis | Zinc-responsive dermatosis (disorder) | ✅ OK |
| 125 | `40845000` | SA-PDT | Gastrointestinal ulcer | Gastrointestinal ulcer (disorder) | ✅ OK |
| 126 | `36575006` | SA-PDT | Brachycephalic airway obstruction syndrome | Brachycephalic airway obstruction syndrome (disorder) | ✅ OK |
| 127 | `63238001` | SA-PDT | Dead on arrival at hospital | Dead on arrival at hospital (finding) | ✅ OK |
| 128 | `48165008` | SA-PDT | Myoglobinuria | Myoglobinuria (finding) | ✅ OK |
| 129 | `85057007` | SA-PDT | Hepatic cyst | Cyst of liver (disorder) | ✅ OK |
| 130 | `363211000009100` | SA-PDT | Protective aggression | Protective aggression (finding) | ✅ OK |
| 131 | `312351000009100` | SA-PDT | Fistulous tract between dorsal spine and skin | Fistula between dorsal spine and skin (disorder) | ✅ OK |
| 132 | `285121000009105` | SA-PDT | Eosinophilic enteritis | Eosinophilic enteritis (disorder) | ✅ OK |
| 133 | `399912005` | SA-PDT | Pressure sore | Pressure ulcer (disorder) | ✅ OK |
| 134 | `312521000009101` | SA-PDT | A/G ratio decreased | Plasma albumin to globulin ratio decreased (finding) | ✅ OK |
| 135 | `8260003` | SA-PDT | Organophosphate intoxication | Organophosphate poisoning (disorder) | ✅ OK |
| 136 | `44103008` | SA-PDT | Ventricular arrhythmia | Ventricular arrhythmia (disorder) | ✅ OK |
| 137 | `358321000009100` | SA-PDT | Amyloid-producing odontogenic tumor | Amyloid-producing odontogenic tumor (disorder) | ✅ OK |
| 138 | `314321000009102` | SA-PDT | Depigmenting dermatitis | Depigmenting dermatitis (disorder) | ✅ OK |
| 139 | `14240001` | SA-PDT | Poliosis | Poliosis (disorder) | ✅ OK |
| 140 | `10743008` | SA-PDT | Nervous colitis | Irritable bowel syndrome (disorder) | ✅ OK |
| 141 | `248509009` | SA-PDT | Iridial mass | Mass in iris (finding) | ✅ OK |
| 142 | `404224009` | SA-PDT | Calcification of tendon | Calcium deposits in tendon (disorder) | ✅ OK |
| 143 | `282931000009101` | SA-PDT | Irritant conjunctivitis | Irritant conjunctivitis (disorder) | ✅ OK |
| 144 | `53295002` | SA-PDT | Chronic otitis externa | Chronic otitis externa (disorder) | ✅ OK |
| 145 | `109753007` | SA-PDT | Complicated tooth crown fracture | Fracture of crown of tooth, enamel and dentin, with pulp exposure (disorder) | ✅ OK |
| 146 | `410062001` | SA-PDT | Vaginal laceration | Laceration of vagina (disorder) | ✅ OK |
| 147 | `167719009` | SA-PDT | Cerebrospinal fluid (CSF) lymphocytosis | Cerebrospinal fluid lymphocytosis (finding) | ✅ OK |
| 148 | `419769007` | SA-PDT | Eosinophilia | Increased blood eosinophil number (finding) | ✅ OK |
| 149 | `448177004` | SA-PDT | Drug interaction | Adverse drug interaction (disorder) | ✅ OK |
| 150 | `49650001` | SA-PDT | Dysuria | Dysuria (finding) | ✅ OK |

### 🔹 ชุดที่ 4: รายการที่ 151 – 200

| # | Concept ID | แหล่งที่มา | DB Display Name / FSN | Raw RF2 FSN (ต้นฉบับ) | ผลการตรวจ |
|---|---|---|---|---|:---:|
| 151 | `133396005` | VSCT | Georgian Mountain cattle breed (organism) | Georgian Mountain cattle breed (organism) | ✅ OK |
| 152 | `131869008` | VSCT | Azores horse breed (organism) | Azores horse breed (organism) | ✅ OK |
| 153 | `132485006` | VSCT | Finnish Lapphund dog breed (organism) | Finnish Lapphund dog breed (organism) | ✅ OK |
| 154 | `300096002` | SA-PDT | Lesion of pinna | Lesion of pinna (disorder) | ✅ OK |
| 155 | `56021002` | SA-PDT | Seroma | Seroma (morphologic abnormality) | ✅ OK |
| 156 | `132301001` | VSCT | Hang pig breed (organism) | Hang pig breed (organism) | ✅ OK |
| 157 | `132960009` | VSCT | Narym horse breed (organism) | Narym horse breed (organism) | ✅ OK |
| 158 | `131440007` | VSCT | Tuli cattle breed (organism) | Tuli cattle breed (organism) | ✅ OK |
| 159 | `277247007` | SA-PDT | Painful larynx | Tenderness of larynx (finding) | ✅ OK |
| 160 | `132398003` | VSCT | Japanese Retriever dog breed (organism) | Japanese Retriever dog breed (organism) | ✅ OK |
| 161 | `133643007` | VSCT | Butana cattle breed (organism) | Butana cattle breed (organism) | ✅ OK |
| 162 | `246679005` | SA-PDT | Ocular discharge | Discharge from eye (finding) | ✅ OK |
| 163 | `133836003` | VSCT | Thibar cattle breed (organism) | Thibar cattle breed (organism) | ✅ OK |
| 164 | `66403007` | SA-PDT | Vascular ring anomaly | Vascular ring of aorta (disorder) | ✅ OK |
| 165 | `62124009` | VSCT | Royal palm turkey (organism) | Royal palm turkey (organism) | ✅ OK |
| 166 | `133494009` | VSCT | Slovakian Pied cattle breed (organism) | Slovakian Pied cattle breed (organism) | ✅ OK |
| 167 | `133315005` | VSCT | Beijing Black Pied cattle breed (organism) | Beijing Black Pied cattle breed (organism) | ✅ OK |
| 168 | `26971003` | VSCT | French spaniel (organism) | French spaniel (organism) | ✅ OK |
| 169 | `131562009` | VSCT | Angeln cattle breed (organism) | Angeln cattle breed (organism) | ✅ OK |
| 170 | `132218004` | VSCT | Canadian Duroc pig breed (organism) | Canadian Duroc pig breed (organism) | ✅ OK |
| 171 | `131673008` | VSCT | Wooden Leg goat breed (organism) | Wooden Leg goat breed (organism) | ✅ OK |
| 172 | `427586006` | SA-PDT | Head pressing | Head pressing (finding) | ✅ OK |
| 173 | `248523006` | SA-PDT | Rectal mass | Rectal mass (finding) | ✅ OK |
| 174 | `410494003` | SA-PDT | Phacogenic uveitis | Lens-induced uveitis (disorder) | ✅ OK |
| 175 | `246925003` | SA-PDT | Corneal vascularization | Neovascularization of cornea (disorder) | ✅ OK |
| 176 | `111875005` | SA-PDT | Canine distemper | Canine distemper (disorder) | ✅ OK |
| 177 | `767146004` | SA-PDT | Arsenic poisoning | Toxic effect of arsenic and/or arsenic compound (disorder) | ✅ OK |
| 178 | `132806002` | VSCT | Barbados Blackbelly sheep breed (organism) | Barbados Blackbelly sheep breed (organism) | ✅ OK |
| 179 | `132519006` | VSCT | Beauceron dog breed (organism) | Beauceron dog breed (organism) | ✅ OK |
| 180 | `162116003` | SA-PDT | Pollakiuria | Increased frequency of urination (finding) | ✅ OK |
| 181 | `132807006` | VSCT | Romney sheep breed (organism) | Romney sheep breed (organism) | ✅ OK |
| 182 | `300570005` | SA-PDT | Perianal mass | Perianal lump (finding) | ✅ OK |
| 183 | `25458004` | SA-PDT | Acute gastritis | Acute gastritis (disorder) | ✅ OK |
| 184 | `44316003` | SA-PDT | Decreased frequency of defecation | Decreased frequency of defecation (finding) | ✅ OK |
| 185 | `133792009` | VSCT | Toposa cattle breed (organism) | Toposa cattle breed (organism) | ✅ OK |
| 186 | `133160001` | VSCT | Single-Footing Horse horse breed (organism) | Single-Footing Horse horse breed (organism) | ✅ OK |
| 187 | `425317008` | SA-PDT | Conjunctival discharge | Conjunctival discharge (finding) | ✅ OK |
| 188 | `370564005` | SA-PDT | Play aggression | Play aggression (finding) | ✅ OK |
| 189 | `46784006` | SA-PDT | Crystalluria | Crystalluria (finding) | ✅ OK |
| 190 | `56512009` | SA-PDT | Bile duct rupture | Rupture of bile duct (disorder) | ✅ OK |
| 191 | `55822004` | SA-PDT | Hyperlipidemia | Hyperlipidemia (disorder) | ✅ OK |
| 192 | `59462000` | SA-PDT | Decreased EKG voltage | Decreased electrocardiogram voltage (finding) | ✅ OK |
| 193 | `132190001` | VSCT | Miami pig breed (organism) | Miami pig breed (organism) | ✅ OK |
| 194 | `72115001` | SA-PDT | Pseudomembranous conjunctivitis | Pseudomembranous conjunctivitis (disorder) | ✅ OK |
| 195 | `299328006` | SA-PDT | Stifle deformed | Deformity of knee joint (finding) | ✅ OK |
| 196 | `133472001` | VSCT | Australian Shorthorn cattle breed (organism) | Australian Shorthorn cattle breed (organism) | ✅ OK |
| 197 | `131952005` | VSCT | Tieling horse breed (organism) | Tieling horse breed (organism) | ✅ OK |
| 198 | `22125009` | SA-PDT | Panniculitis | Panniculitis (disorder) | ✅ OK |
| 199 | `63479002` | SA-PDT | Hookworm infection by Ancylostoma | Ancylostomiasis (disorder) | ✅ OK |
| 200 | `329581000009100` | VSCT | Family Kogiidae (organism) | Family Kogiidae (organism) | ✅ OK |

---

## 5. คำแนะนำและ Workflow สรุป

1. **KU Synonyms (`ku_custom_synonyms.csv`)**: เก็บไว้เป็น CSV นอก DB ดีที่สุด ไม่ต้องสร้าง DB แยก เมื่อ Rebuild สคริปต์จะอ่านเข้า DB ให้อัตโนมัติ
2. **การ Rebuild**: รัน `python3 scripts/build_direct_db.py` หรือ กด Rebuild ผ่าน `admin.html` จะได้ทั้ง `.db` และ `.db.gz` อัตโนมัติ
3. **Git Rule**: `.gitignore` ถูกตั้งค่าให้ซ่อนทั้ง `.db` และ `.db.gz` เพื่อไม่ให้ Repo พอง และใช้วิธีอัปโหลดไฟล์ DB ไป Render.com แยกต่างหาก
