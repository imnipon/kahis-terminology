#!/usr/bin/env python3
"""
scripts/build_body_system.py (Ultra-Fast)
Enriches terminology_master_30cols.csv by resolving and appending a 'body_system' column.
Source Resolution Priority: SNOMED CT VET Extension -> SNOMED CT International
"""

import os
import sys
import glob
import csv
import time

def main():
    start_time = time.time()
    print("==================================================")
    print("KAHIS Terminology Master - Body System Enrichment")
    print("==================================================")

    # 1. Discover RF2 files
    vet_rel_files = glob.glob('SnomedCT_VETExtension_PRODUCTION_*/Snapshot/Terminology/sct2_Relationship_Snapshot*.txt')
    inter_rel_files = glob.glob('SnomedCT_InternationalRF2_PRODUCTION_*/Snapshot/Terminology/sct2_Relationship_Snapshot*.txt')
    vet_desc_files = glob.glob('SnomedCT_VETExtension_PRODUCTION_*/Snapshot/Terminology/sct2_Description_Snapshot-en*.txt')
    inter_desc_files = glob.glob('SnomedCT_InternationalRF2_PRODUCTION_*/Snapshot/Terminology/sct2_Description_Snapshot-en*.txt')

    if not vet_rel_files or not inter_rel_files:
        print("ERROR: Could not find RF2 relationship files in workspace!")
        sys.exit(1)

    vet_rel_path = vet_rel_files[0]
    inter_rel_path = inter_rel_files[0]
    vet_desc_path = vet_desc_files[0]
    inter_desc_path = inter_desc_files[0]

    # Load master CIDs first to filter relationships
    print("[1/4] Reading terminology_master_30cols.csv concept IDs...")
    master_cids = set()
    with open('terminology_master_30cols.csv', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        scid_idx = header.index('snomed_concept_id')
        spid_idx = header.index('sapdt_concept_id')
        for row in reader:
            if len(row) > scid_idx and row[scid_idx]:
                master_cids.add(row[scid_idx])
            if len(row) > spid_idx and row[spid_idx]:
                master_cids.add(row[spid_idx])

    print(f"  Target Master Concept IDs: {len(master_cids)}")

    # 2. Load Descriptions FSN
    print("[2/4] Loading FSN descriptions...")
    fsn_map = {}
    for desc_path in [inter_desc_path, vet_desc_path]:
        with open(desc_path, encoding='utf-8') as f:
            f.readline() # header
            for line in f:
                parts = line.rstrip('\r\n').split('\t')
                if len(parts) > 7 and parts[2] == '1' and parts[6] == '900000000000003001':
                    fsn_map[parts[4]] = parts[7]

    print(f"  Loaded FSNs: {len(fsn_map)}")

    # 3. Load Relationship Graphs
    print("[3/4] Loading relationships (IS-A, Finding site, Procedure site)...")
    def load_graph(path):
        parents = {}
        finding_sites = {}
        proc_sites = {}
        with open(path, encoding='utf-8') as f:
            f.readline()
            for line in f:
                parts = line.rstrip('\r\n').split('\t')
                if len(parts) > 7 and parts[2] == '1': # active
                    src, dst, rel_type = parts[4], parts[5], parts[7]
                    if rel_type == '116680003': # IS A
                        parents.setdefault(src, set()).add(dst)
                    elif rel_type == '363698007': # Finding site
                        finding_sites.setdefault(src, set()).add(dst)
                    elif rel_type in ('363704007', '405813007', '405814008'): # Procedure site
                        proc_sites.setdefault(src, set()).add(dst)
        return parents, finding_sites, proc_sites

    vet_parents, vet_fs, vet_ps = load_graph(vet_rel_path)
    inter_parents, inter_fs, inter_ps = load_graph(inter_rel_path)

    print(f"  Loaded relationships in {time.time() - start_time:.2f}s")

    # Map of Body System category CIDs to Clean Names
    BODY_SYSTEM_MAP = {
        '272625008': 'Digestive system',
        '278887002': 'Digestive system',
        '20139000':  'Respiratory system',
        '113257007': 'Cardiovascular system',
        '119235005': 'Nervous system',
        '26107004':  'Musculoskeletal system',
        '362965005': 'Reproductive system',
        '278891008': 'Reproductive system',
        '122489005': 'Urinary system',
        '118671006': 'Endocrine system',
        '244184003': 'Integumentary system (Skin)',
        '181750001': 'Immune system',
        '278896008': 'Lymphatic system',
        '361077002': 'Visual system (Eye)',
        '361078007': 'Auditory system (Ear)',
        '362874006': 'Hematopoietic system (Blood)',
        '278198002': 'Systemic / Body as a whole',
        '127954009': 'Head and neck structure',
    }

    for cid in inter_parents.get('280115004', set()):
        if cid not in BODY_SYSTEM_MAP:
            raw_fsn = fsn_map.get(cid, '')
            clean = raw_fsn.replace(' structure', '').replace(' (body structure)', '').replace(' (body system)', '').strip()
            if clean:
                BODY_SYSTEM_MAP[cid] = clean

    def clean_system_name(name):
        return name.replace(' structure', '').replace(' (body structure)', '').replace(' (body system)', '').strip()

    # Fast Memoized Resolution
    memo_cache = {}

    def resolve_body_system(cid, parents_dict, fs_dict, ps_dict, source_tag):
        cache_key = (cid, source_tag)
        if cache_key in memo_cache:
            return memo_cache[cache_key]

        if not cid:
            return None

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
                    if node in BODY_SYSTEM_MAP:
                        resolved.add(clean_system_name(BODY_SYSTEM_MAP[node]))
                    for p in parents_dict.get(node, []):
                        next_level.add(p)
                if not next_level or resolved:
                    break
                curr_level = next_level

        res = " | ".join(sorted(resolved)) if resolved else None
        memo_cache[cache_key] = res
        return res

    # 4. Process CSV and Write Output
    print("[4/4] Writing terminology_master_31cols.csv...")
    input_csv = 'terminology_master_30cols.csv'
    output_csv = 'terminology_master_31cols.csv'

    with open(input_csv, encoding='utf-8-sig') as f_in, open(output_csv, 'w', encoding='utf-8', newline='') as f_out:
        reader = csv.reader(f_in)
        writer = csv.writer(f_out)

        header = next(reader)
        stype_idx = header.index('snomed_semantic_type')
        scid_idx = header.index('snomed_concept_id')
        spid_idx = header.index('sapdt_concept_id')

        new_header = header.copy()
        new_header.insert(stype_idx + 1, 'body_system')
        writer.writerow(new_header)

        total_rows = 0
        vet_resolved = 0
        inter_resolved = 0
        fallback_count = 0
        system_stats = {}

        for row in reader:
            total_rows += 1
            scid = row[scid_idx] if len(row) > scid_idx else ''
            spid = row[spid_idx] if len(row) > spid_idx else ''
            stype = row[stype_idx] if len(row) > stype_idx else ''

            target_cid = scid or spid
            body_system = None

            # Priority 1: VET
            if target_cid:
                body_system = resolve_body_system(target_cid, vet_parents, vet_fs, vet_ps, 'VET')
                if body_system:
                    vet_resolved += 1

            # Priority 2: SCT Inter Fallback
            if not body_system and target_cid:
                body_system = resolve_body_system(target_cid, inter_parents, inter_fs, inter_ps, 'INTER')
                if body_system:
                    inter_resolved += 1

            # Priority 3: Semantic Fallback
            if not body_system:
                fallback_count += 1
                if stype in ('organism', 'cell'):
                    body_system = 'Organism / Microorganism'
                elif stype in ('substance', 'product', 'medicinal product'):
                    body_system = 'Substance / Product'
                elif stype in ('qualifier value', 'foundation metadata concept'):
                    body_system = 'Qualifier / Metadata'
                elif stype in ('physical object', 'physical force'):
                    body_system = 'Physical Object / Environment'
                else:
                    body_system = 'Systemic / Not Applicable (N/A)'

            system_stats[body_system] = system_stats.get(body_system, 0) + 1

            new_row = row.copy()
            new_row.insert(stype_idx + 1, body_system)
            writer.writerow(new_row)

    print("\n==================================================")
    print("SUCCESS: Body System Enrichment Complete!")
    print("==================================================")
    print(f"Total Master Rows processed : {total_rows}")
    print(f"Resolved via VSCT (VET)     : {vet_resolved} ({vet_resolved/total_rows*100:.2f}%)")
    print(f"Resolved via SCT Inter      : {inter_resolved} ({inter_resolved/total_rows*100:.2f}%)")
    print(f"Semantic Fallback           : {fallback_count} ({fallback_count/total_rows*100:.2f}%)")
    print(f"Total Execution Time        : {time.time() - start_time:.2f}s")
    print(f"Output File                 : {output_csv}")

    print("\nTop 15 Body Systems Distribution:")
    sorted_stats = sorted(system_stats.items(), key=lambda x: x[1], reverse=True)
    for sys_name, count in sorted_stats[:15]:
        print(f"  - {sys_name:<35}: {count:>6} ({count/total_rows*100:.2f}%)")

if __name__ == '__main__':
    main()
