#!/usr/bin/env python3
"""
server.py
HTTP Server & REST API for SA-PDT & SNOMED CT Veterinary Extension for KAHIS
Implements multi-word AND search, concept grouping, and filter hit counters.
"""

import http.server
import socketserver
import json
import sqlite3
import urllib.parse
import os
import sys
import time
import glob
import re

PORT = int(os.environ.get('PORT', 8080))

# -- BUG-02 FIX: Resolve all paths from this script's own location --
# This ensures the server works correctly regardless of:
#   - Current Working Directory (CWD) when server is launched
#   - Drive letter (C:\ vs D:\ on Windows)
#   - Username or home directory (/Users/nipon vs /Users/other)
#   - Project folder name (ku-sa-pdt or any other name)
APP_DIR   = os.path.dirname(os.path.abspath(__file__))  # .../kahis-terminology-app/
KAHIS_DIR = os.path.dirname(APP_DIR)                     # .../kahis-terminology/
DB_FILE   = os.path.join(APP_DIR, 'terminology_search.db')
STATIC_DIR = os.path.join(APP_DIR, 'static')

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def get_release_versions():
    """Auto-detect release dates from source folder names under KAHIS_DIR."""
    sapdt_date = "N/A"
    vsct_date  = "N/A"
    sct_date   = "N/A"

    # SA-PDT: look for folder matching SA-PDT* and find 8-digit date inside it
    sapdt_dirs = glob.glob(os.path.join(KAHIS_DIR, 'SA-PDT*'))
    if sapdt_dirs:
        m = re.search(r'(\d{8})', os.path.basename(sapdt_dirs[0]))
        if m: sapdt_date = m.group(1)
        else:
            # Try reading release file name inside the folder
            rel_files = glob.glob(os.path.join(sapdt_dirs[0], 'SA-PDTReleaseFile_full_*.txt'))
            if rel_files:
                m2 = re.search(r'(\d{8})', os.path.basename(rel_files[0]))
                if m2: sapdt_date = m2.group(1)

    # VSCT: look for SnomedCT_VETExtension_* folder
    vsct_dirs = glob.glob(os.path.join(KAHIS_DIR, 'SnomedCT_VETExtension_*'))
    if vsct_dirs:
        m = re.search(r'(\d{8})', os.path.basename(vsct_dirs[0]))
        if m: vsct_date = m.group(1)

    # SCT International: look for SnomedCT_InternationalRF2_* folder
    sct_dirs = glob.glob(os.path.join(KAHIS_DIR, 'SnomedCT_InternationalRF2_*'))
    if sct_dirs:
        m = re.search(r'(\d{8})', os.path.basename(sct_dirs[0]))
        if m: sct_date = m.group(1)

    return {
        'sapdt': f"SA-PDT {sapdt_date}",
        'vsct':  f"VSCT {vsct_date}",
        'sct':   f"SCT {sct_date}"
    }

class TerminologyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        if path == '/api/search':
            self.handle_api_search(query_params)
        elif path.startswith('/api/concept/'):
            concept_id = path.split('/')[-1]
            self.handle_api_concept(concept_id)
        elif path == '/api/filters':
            self.handle_api_filters()
        elif path == '/api/release_versions':
            self.send_json(get_release_versions())
        elif path == '/api/admin/stats':
            self.handle_admin_stats()
        elif path == '/api/admin/export/master':
            self.handle_export_master()
        elif path == '/api/admin/export/ku':
            self.handle_export_ku()
        elif path == '/api/admin/rebuild':
            # GET /api/admin/rebuild — Server-Sent Events stream of build progress
            self.handle_rebuild_stream()
        elif path == '/api/ku_synonym':
            # GET /api/ku_synonym?concept_id=XXX  — list ku synonyms for a concept
            cid = query_params.get('concept_id', [''])[0]
            self.handle_get_ku_synonyms(cid)
        else:
            if path == '/':
                self.path = '/index.html'
            super().do_GET()

    def do_OPTIONS(self):
        """Handle CORS preflight requests from admin.html."""
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        """Handle POST requests: add/delete ku synonyms."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # Read JSON body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b'{}'
        try:
            data = json.loads(body.decode('utf-8'))
        except Exception:
            self.send_json({'error': 'Invalid JSON body'}, status=400)
            return

        if path == '/api/ku_synonym/add':
            self.handle_add_ku_synonym(data)
        elif path == '/api/ku_synonym/delete':
            self.handle_delete_ku_synonym(data)
        elif path == '/api/admin/rebuild':
            # POST /api/admin/rebuild — same as GET (trigger rebuild, stream response)
            self.handle_rebuild_stream()
        else:
            self.send_json({'error': 'Not found'}, status=404)

    def handle_rebuild_stream(self):
        """GET /api/admin/rebuild — Server-Sent Events streaming of build_direct_db.py."""
        import subprocess
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts', 'build_direct_db.py')
        if not os.path.exists(script):
            self.send_json({'error': f'build_direct_db.py not found at {script}'}, status=404)
            return

        # SSE headers
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('X-Accel-Buffering', 'no')
        self.end_headers()

        def sse(event, data):
            msg = f'event: {event}\ndata: {data}\n\n'
            self.wfile.write(msg.encode('utf-8'))
            self.wfile.flush()

        try:
            proc = subprocess.Popen(
                [sys.executable, script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            for line in proc.stdout:
                sse('log', line.rstrip())
            proc.wait()
            if proc.returncode == 0:
                sse('done', '✅ Build สำเร็จ — DB พร้อมใช้งาน')
            else:
                sse('error', f'❌ Build ล้มเหลว (exit code {proc.returncode})')
        except Exception as e:
            try:
                sse('error', f'❌ Exception: {e}')
            except Exception:
                pass

    def handle_admin_stats(self):

        """GET /api/admin/stats — returns 7 dashboard statistics."""
        ACTIVE_COND   = "((in_sapdt='Yes' AND sapdt_status='Active') OR (in_vsct='Yes' AND snomed_active='Yes'))"
        INACTIVE_COND = "NOT ((in_sapdt='Yes' AND sapdt_status='Active') OR (in_vsct='Yes' AND snomed_active='Yes'))"
        try:
            conn = get_db()
            cur = conn.cursor()

            def q1(sql):
                cur.execute(sql)
                return cur.fetchone()[0]

            total    = q1("SELECT COUNT(DISTINCT COALESCE(NULLIF(snomed_concept_id,''),sapdt_concept_id)) FROM terms WHERE in_sapdt='Yes' OR in_vsct='Yes'")
            active   = q1(f"SELECT COUNT(DISTINCT COALESCE(NULLIF(snomed_concept_id,''),sapdt_concept_id)) FROM terms WHERE {ACTIVE_COND}")
            inactive = q1(f"SELECT COUNT(DISTINCT COALESCE(NULLIF(snomed_concept_id,''),sapdt_concept_id)) FROM terms WHERE {INACTIVE_COND} AND (in_sapdt='Yes' OR in_vsct='Yes')")

            ku_syns  = 0
            try:
                cur.execute("SELECT COUNT(*) FROM ku_synonym_text")
                ku_syns = cur.fetchone()[0]
            except Exception:
                pass  # table not yet created

            sapdt_vsct = q1("SELECT COUNT(*) FROM terms WHERE in_sapdt='Yes' AND in_vsct='Yes'")
            sapdt_sct  = q1("SELECT COUNT(*) FROM terms WHERE in_sapdt='Yes' AND in_sct_inter='Yes' AND in_vsct!='Yes'")
            vsct_only  = q1("SELECT COUNT(*) FROM terms WHERE in_vsct='Yes' AND in_sapdt!='Yes'")

            conn.close()
            self.send_json({
                'total':          total,
                'active':         active,
                'inactive':       inactive,
                'ku_synonyms':    ku_syns,
                'sapdt_and_vsct': sapdt_vsct,
                'sapdt_and_sct':  sapdt_sct,
                'vsct_only':      vsct_only
            })
        except Exception as e:
            self.send_json({'error': str(e)}, status=500)

    def handle_export_master(self):
        """GET /api/admin/export/master — stream master CSV file."""
        import csv, io
        output_dir = os.path.join(APP_DIR, '..', 'output')
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, 'master_kahis_terminology.csv')
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM terms ORDER BY id")
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            conn.close()

            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(cols)
            writer.writerows(rows)
            csv_bytes = buf.getvalue().encode('utf-8-sig')  # BOM for Excel

            # Also save to output/
            with open(out_path, 'wb') as f:
                f.write(csv_bytes)

            self.send_response(200)
            self.send_header('Content-Type', 'text/csv; charset=utf-8')
            self.send_header('Content-Disposition', 'attachment; filename="master_kahis_terminology.csv"')
            self.send_header('Content-Length', str(len(csv_bytes)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(csv_bytes)
        except Exception as e:
            self.send_json({'error': str(e)}, status=500)

    def handle_export_ku(self):
        """GET /api/admin/export/ku — stream ku_custom_synonyms CSV."""
        import csv, io
        output_dir = os.path.join(APP_DIR, '..', 'output')
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, 'ku_custom_synonyms.csv')
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT k.id, k.concept_id, t.display_name, t.snomed_fsn,
                       k.ku_synonym_text, k.lang_tag, k.created_at
                FROM ku_synonym_text k
                LEFT JOIN terms t ON (t.snomed_concept_id = k.concept_id OR t.sapdt_concept_id = k.concept_id)
                ORDER BY k.concept_id, k.id
            """)
            cols = ['id','concept_id','display_name','snomed_fsn','ku_synonym_text','lang_tag','created_at']
            rows = cur.fetchall()
            conn.close()

            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(cols)
            writer.writerows(rows)
            csv_bytes = buf.getvalue().encode('utf-8-sig')

            with open(out_path, 'wb') as f:
                f.write(csv_bytes)

            self.send_response(200)
            self.send_header('Content-Type', 'text/csv; charset=utf-8')
            self.send_header('Content-Disposition', 'attachment; filename="ku_custom_synonyms.csv"')
            self.send_header('Content-Length', str(len(csv_bytes)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(csv_bytes)
        except Exception as e:
            self.send_json({'error': str(e)}, status=500)

    def handle_get_ku_synonyms(self, concept_id):

        """GET /api/ku_synonym?concept_id=XXX"""
        if not concept_id:
            self.send_json({'error': 'concept_id required'}, status=400)
            return
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                'SELECT id, ku_synonym_text, lang_tag, created_at FROM ku_synonym_text WHERE concept_id = ? ORDER BY id',
                (concept_id,)
            )
            rows = [{'id': r[0], 'text': r[1], 'lang': r[2], 'created_at': r[3]} for r in cur.fetchall()]
            conn.close()
            self.send_json({'concept_id': concept_id, 'synonyms': rows})
        except Exception as e:
            self.send_json({'error': str(e)}, status=500)

    def handle_add_ku_synonym(self, data):
        """POST /api/ku_synonym/add  body: {concept_id, text, lang?}"""
        concept_id = (data.get('concept_id') or '').strip()
        text       = (data.get('text') or '').strip()
        lang_tag   = (data.get('lang') or 'ku').strip()

        if not concept_id or not text:
            self.send_json({'error': 'concept_id and text are required'}, status=400)
            return
        if len(text) > 500:
            self.send_json({'error': 'text too long (max 500 chars)'}, status=400)
            return
        try:
            conn = get_db()
            cur = conn.cursor()
            # Prevent exact duplicate
            cur.execute(
                'SELECT id FROM ku_synonym_text WHERE concept_id = ? AND ku_synonym_text = ?',
                (concept_id, text)
            )
            if cur.fetchone():
                conn.close()
                self.send_json({'error': 'Duplicate synonym already exists'}, status=409)
                return
            cur.execute(
                'INSERT INTO ku_synonym_text (concept_id, ku_synonym_text, lang_tag) VALUES (?, ?, ?)',
                (concept_id, text, lang_tag)
            )
            conn.commit()
            new_id = cur.lastrowid
            conn.close()
            self.send_json({'ok': True, 'id': new_id, 'concept_id': concept_id, 'text': text})
        except Exception as e:
            self.send_json({'error': str(e)}, status=500)

    def handle_delete_ku_synonym(self, data):
        """POST /api/ku_synonym/delete  body: {id}"""
        syn_id = data.get('id')
        if syn_id is None:
            self.send_json({'error': 'id required'}, status=400)
            return
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute('DELETE FROM ku_synonym_text WHERE id = ?', (int(syn_id),))
            deleted = cur.rowcount
            conn.commit()
            conn.close()
            if deleted == 0:
                self.send_json({'error': f'No row with id={syn_id}'}, status=404)
            else:
                self.send_json({'ok': True, 'deleted_id': syn_id})
        except Exception as e:
            self.send_json({'error': str(e)}, status=500)

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def handle_api_filters(self):
        conn = get_db()
        cursor = conn.cursor()

        # CONFLICT-01 FIX: Active = SA-PDT Active OR VSCT Active (OR logic, not AND)
        # Old (wrong): only show if SA-PDT active; if in_sapdt='Yes' it ignored VSCT status entirely
        # New (correct): show if ANY of the sources is active
        active_where = """
        WHERE (in_sapdt = 'Yes' OR in_vsct = 'Yes')
          AND (
            (in_sapdt = 'Yes' AND sapdt_status = 'Active')
            OR
            (in_vsct = 'Yes' AND snomed_active = 'Yes')
          )
        """

        cursor.execute(f"SELECT DISTINCT snomed_semantic_type FROM terms {active_where} AND snomed_semantic_type != '' ORDER BY snomed_semantic_type")
        semantic_types = [row[0] for row in cursor.fetchall()]

        cursor.execute(f"SELECT DISTINCT body_system FROM terms {active_where} AND body_system != '' ORDER BY body_system")
        body_systems = [row[0] for row in cursor.fetchall()]

        conn.close()
        self.send_json({
            'semantic_types': semantic_types,
            'body_systems': body_systems,
            'release_versions': get_release_versions()
        })

    def handle_api_search(self, params):
        """GET /api/search?q=...&semantic_type=...&status=..."""
        t0 = time.time()
        q = params.get('q', [''])[0].strip()
        stypes = params.get('semantic_type', [])
        status_mode = params.get('status', ['active'])[0].lower()
        group_by = params.get('group_by_concept', ['true'])[0].lower() == 'true'
        limit = int(params.get('limit', ['50'])[0])
        offset = int(params.get('offset', ['0'])[0])

        conn = get_db()
        cursor = conn.cursor()

        # Rule 2: Must be in SA-PDT and/or VSCT
        where_clauses = ["(in_sapdt = 'Yes' OR in_vsct = 'Yes')"]

        # CONFLICT-01 FIX: Active/Inactive uses OR logic
        # Active  = SA-PDT Active  OR  VSCT Active
        # Inactive = NOT (SA-PDT Active OR VSCT Active)  AND still in SA-PDT/VSCT
        ACTIVE_COND   = "((in_sapdt = 'Yes' AND sapdt_status = 'Active') OR (in_vsct = 'Yes' AND snomed_active = 'Yes'))"
        INACTIVE_COND = "NOT ((in_sapdt = 'Yes' AND sapdt_status = 'Active') OR (in_vsct = 'Yes' AND snomed_active = 'Yes'))"

        if status_mode == 'active':
            where_clauses.append(ACTIVE_COND)
        elif status_mode == 'inactive':
            where_clauses.append(INACTIVE_COND)

        sql_params = []

        # Multi-word AND search condition (e.g. 'shou frac')
        if q:
            if q.isdigit():
                where_clauses.append("(snomed_concept_id LIKE ? OR sapdt_concept_id LIKE ? OR sapdt_description_id LIKE ?)")
                sql_params.extend([f"{q}%", f"{q}%", f"{q}%"])
            else:
                clean_q = q.replace('"', '').replace("'", "")
                words = clean_q.split()
                for word in words:
                    where_clauses.append("""
                    (display_name LIKE ? OR synonym LIKE ? OR snomed_fsn LIKE ? OR sapdt_fsn LIKE ? OR 
                     snomed_preferred_term LIKE ? OR snomed_all_synonyms LIKE ? OR 
                     COALESCE(snomed_concept_id, sapdt_concept_id) IN (
                         SELECT concept_id FROM ku_synonym_text WHERE ku_synonym_text LIKE ?
                     ))
                    """)
                    like_pat = f"%{word}%"
                    sql_params.extend([like_pat, like_pat, like_pat, like_pat, like_pat, like_pat, like_pat])

        # Multi-select Semantic Types filter
        if stypes and len(stypes) > 0 and stypes[0] != '':
            st_clauses = []
            for st in stypes:
                st_clauses.append("snomed_semantic_type LIKE ?")
                sql_params.append(f"%{st}%")
            where_clauses.append("(" + " OR ".join(st_clauses) + ")")

        where_sql = " WHERE " + " AND ".join(where_clauses)
        group_sql = " GROUP BY COALESCE(NULLIF(snomed_concept_id,''), sapdt_concept_id) " if group_by else ""

        # Total count query & row fetching
        rows = []
        if not q:
            total_count = 0
        elif group_by:
            count_sql = f"SELECT COUNT(DISTINCT COALESCE(NULLIF(snomed_concept_id,''), sapdt_concept_id)) FROM terms{where_sql}"
            cursor.execute(count_sql, sql_params)
            total_count = cursor.fetchone()[0]

            first_word = q.split()[0] if q else ""
            data_sql = f"""
            SELECT id, display_name, in_sapdt, in_vsct, in_sct_inter, sapdt_concept_id,
                   snomed_concept_id, snomed_fsn, snomed_preferred_term, snomed_semantic_type,
                   body_system, match_type, synonym,
                   snomed_definition_status, sapdt_status, snomed_active
            FROM terms
            {where_sql}
            {group_sql}
            ORDER BY
                CASE WHEN display_name LIKE ? THEN 1 ELSE 2 END,
                length(display_name) ASC
            LIMIT ? OFFSET ?
            """
            prefix_pat = f"{first_word}%"
            full_params = sql_params + [prefix_pat, limit, offset]
            cursor.execute(data_sql, full_params)
            rows = [dict(row) for row in cursor.fetchall()]
        else:
            # Group by Concept = False: Expand matching synonyms as individual term rows
            first_word = q.split()[0] if q else ""
            all_data_sql = f"""
            SELECT id, display_name, in_sapdt, in_vsct, in_sct_inter, sapdt_concept_id,
                   snomed_concept_id, snomed_fsn, snomed_preferred_term, snomed_all_synonyms,
                   snomed_semantic_type, body_system, match_type, synonym,
                   snomed_definition_status, sapdt_status, snomed_active
            FROM terms {where_sql}
            ORDER BY CASE WHEN display_name LIKE ? THEN 1 ELSE 2 END, length(display_name) ASC
            """
            prefix_pat = f"{first_word}%"
            cursor.execute(all_data_sql, sql_params + [prefix_pat])
            raw_concepts = [dict(row) for row in cursor.fetchall()]

            expanded_rows = []
            clean_q = q.replace('"', '').replace("'", "").lower()
            words = clean_q.split()

            for r in raw_concepts:
                main_name = r.get('display_name') or r.get('snomed_preferred_term') or ''
                expanded_rows.append(r)
                seen_terms = {main_name.lower()}

                syn_str = (r.get('synonym') or '') + '|' + (r.get('snomed_all_synonyms') or '')
                for s in syn_str.split('|'):
                    s_clean = s.strip()
                    if not s_clean or s_clean.lower() in seen_terms:
                        continue
                    if not q.isdigit() and any(w in s_clean.lower() for w in words):
                        seen_terms.add(s_clean.lower())
                        syn_row = dict(r)
                        syn_row['display_name'] = s_clean
                        syn_row['snomed_fsn'] = f"{s_clean} (Synonym of {main_name})"
                        expanded_rows.append(syn_row)

            total_count = len(expanded_rows)
            rows = expanded_rows[offset:offset+limit]

        # Global Search Extension: Query concept_terms for SCT International Only concepts
        global_search = params.get('global_search', ['false'])[0].lower() == 'true'
        if global_search and q:
            existing_cids = {str(r.get('snomed_concept_id') or r.get('sapdt_concept_id')) for r in rows if r.get('snomed_concept_id') or r.get('sapdt_concept_id')}
            
            if q.isdigit():
                ct_sql = "SELECT DISTINCT concept_id, term, semantic_type FROM concept_terms WHERE concept_id LIKE ? LIMIT 100"
                ct_params = [f"{q}%"]
            else:
                clean_q = q.replace('"', '').replace("'", "")
                first_w = clean_q.split()[0]
                ct_sql = "SELECT DISTINCT concept_id, term, semantic_type FROM concept_terms WHERE term LIKE ? LIMIT 100"
                ct_params = [f"%{first_w}%"]

            cursor.execute(ct_sql, ct_params)
            ct_rows = [dict(r) for r in cursor.fetchall()]
            
            extra_sct_rows = []
            for cr in ct_rows:
                cid = str(cr['concept_id'])
                if cid not in existing_cids:
                    existing_cids.add(cid)
                    extra_sct_rows.append({
                        'id': f"ct_{cid}",
                        'display_name': cr['term'],
                        'sapdt_concept_id': '',
                        'snomed_concept_id': cid,
                        'snomed_fsn': cr['term'],
                        'snomed_preferred_term': cr['term'],
                        'snomed_semantic_type': cr['semantic_type'] or 'concept',
                        'body_system': 'Systemic / Not Applicable (N/A)',
                        'match_type': 'sct_inter_only',
                        'synonym': '',
                        'in_sapdt': 'No',
                        'in_vsct': 'No',
                        'in_sct_inter': 'Yes',
                        'sapdt_status': 'Inactive',
                        'snomed_active': 'Yes'
                    })
            
            total_count += len(extra_sct_rows)
            needed = max(0, limit - len(rows))
            if needed > 0:
                rows.extend(extra_sct_rows[:needed])

        # Dynamic Hit Counters for semantic filter
        semantic_counts = {}

        if q:
            base_where = ["(in_sapdt = 'Yes' OR in_vsct = 'Yes')"]
            # CONFLICT-01 FIX: same OR-based active logic for semantic counts
            if status_mode == 'active':
                base_where.append("((in_sapdt = 'Yes' AND sapdt_status = 'Active') OR (in_vsct = 'Yes' AND snomed_active = 'Yes'))")
            
            base_params = []
            if q.isdigit():
                base_where.append("(snomed_concept_id LIKE ? OR sapdt_concept_id LIKE ? OR sapdt_description_id LIKE ?)")
                base_params.extend([f"{q}%", f"{q}%", f"{q}%"])
            else:
                clean_q = q.replace('"', '').replace("'", "")
                words = clean_q.split()
                for word in words:
                    base_where.append("(display_name LIKE ? OR synonym LIKE ? OR snomed_fsn LIKE ? OR sapdt_fsn LIKE ?)")
                    like_pat = f"%{word}%"
                    base_params.extend([like_pat, like_pat, like_pat, like_pat])

            base_sql = " WHERE " + " AND ".join(base_where)

            # Semantic Counts
            st_count_sql = f"""
            SELECT snomed_semantic_type, COUNT(DISTINCT COALESCE(NULLIF(snomed_concept_id,''), sapdt_concept_id)) 
            FROM terms {base_sql} GROUP BY snomed_semantic_type
            """
            cursor.execute(st_count_sql, base_params)
            for st_val, cnt in cursor.fetchall():
                if st_val:
                    semantic_counts[st_val.lower()] = cnt

        conn.close()
        elapsed_sec = round(time.time() - t0, 2)

        self.send_json({
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'elapsed_sec': elapsed_sec,
            'results': rows,
            'semantic_counts': semantic_counts
        })

    def handle_api_concept(self, concept_id):
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM terms WHERE snomed_concept_id = ? OR sapdt_concept_id = ?", (concept_id, concept_id))
        master_rows = [dict(row) for row in cursor.fetchall()]

        main_row = {}
        if master_rows:
            main_row = master_rows[0]
        else:
            cursor.execute("SELECT term, semantic_type FROM concept_terms WHERE concept_id = ?", (concept_id,))
            ct = cursor.fetchone()
            term_str = ct['term'] if ct else concept_id
            stype = ct['semantic_type'] if ct else ''
            main_row = {
                'display_name': term_str,
                'snomed_concept_id': concept_id,
                'sapdt_concept_id': '',
                'snomed_fsn': term_str,
                'snomed_preferred_term': term_str,
                'sapdt_fsn': '',
                'snomed_semantic_type': stype,
                'body_system': 'Systemic / Not Applicable (N/A)',
                'in_sapdt': 'No',
                'in_vsct': 'No',
                'in_sct_inter': 'Yes'
            }
            master_rows = [main_row]

        def get_concept_meta(cid):
            cursor.execute("""
            SELECT display_name, in_sapdt, in_vsct, in_sct_inter, sapdt_status, snomed_active,
                   sapdt_concept_id, snomed_concept_id, snomed_semantic_type
            FROM terms WHERE snomed_concept_id = ? OR sapdt_concept_id = ? LIMIT 1
            """, (cid, cid))
            res = cursor.fetchone()
            if res:
                d = dict(res)
                is_act = (d.get('in_sapdt') == 'Yes' and d.get('sapdt_status') == 'Active') or \
                         (d.get('in_vsct') == 'Yes' and d.get('snomed_active') == 'Yes')
                d['is_active'] = is_act
                return d

            cursor.execute("SELECT term, semantic_type FROM concept_terms WHERE concept_id = ?", (cid,))
            ct = cursor.fetchone()
            term_str = ct['term'] if ct else cid
            stype = ct['semantic_type'] if ct else ''
            # VSCT extension IDs always contain the extension namespace '1000009'
            is_vsct = 'Yes' if '1000009' in str(cid) else 'No'
            return {
                'display_name': term_str,
                'in_sapdt': 'No',
                'in_vsct': is_vsct,
                'in_sct_inter': 'Yes',
                'sapdt_concept_id': '',
                'snomed_concept_id': cid,
                'snomed_semantic_type': stype,
                'is_active': True
            }

        # Parents
        cursor.execute("""
        SELECT r.destination_id as concept_id
        FROM relationships r
        WHERE r.source_id = ? AND r.type_id = '116680003'
        """, (concept_id,))
        parent_cids = [row[0] for row in cursor.fetchall()]
        parents = []
        for pcid in parent_cids:
            meta = get_concept_meta(pcid)
            parents.append({
                'concept_id': pcid,
                'term': meta.get('display_name', pcid),
                'in_sapdt': meta.get('in_sapdt', 'No'),
                'in_vsct': meta.get('in_vsct', 'No'),
                'in_sct_inter': meta.get('in_sct_inter', 'Yes'),
                'semantic_type': meta.get('snomed_semantic_type', ''),
                'is_active': meta.get('is_active', True)
            })

        # Children — CONFLICT-03 FIX: count total first, then fetch first 50
        cursor.execute("""
        SELECT COUNT(*) FROM relationships
        WHERE destination_id = ? AND type_id = '116680003'
        """, (concept_id,))
        children_total_count = cursor.fetchone()[0]

        cursor.execute("""
        SELECT r.source_id as concept_id
        FROM relationships r
        WHERE r.destination_id = ? AND r.type_id = '116680003'
        LIMIT 50
        """, (concept_id,))
        child_cids = [row[0] for row in cursor.fetchall()]
        children = []
        for ccid in child_cids:
            meta = get_concept_meta(ccid)
            children.append({
                'concept_id': ccid,
                'term': meta.get('display_name', ccid),
                'in_sapdt': meta.get('in_sapdt', 'No'),
                'in_vsct': meta.get('in_vsct', 'No'),
                'in_sct_inter': meta.get('in_sct_inter', 'Yes'),
                'semantic_type': meta.get('snomed_semantic_type', ''),
                'is_active': meta.get('is_active', True)
            })

        # Attributes
        cursor.execute("""
        SELECT r.type_name, r.destination_id as concept_id
        FROM relationships r
        WHERE r.source_id = ? AND r.type_id != '116680003'
        """, (concept_id,))
        attr_rows = cursor.fetchall()
        attributes = []
        for a_type, acid in attr_rows:
            meta = get_concept_meta(acid)
            attributes.append({
                'type_name': a_type,
                'concept_id': acid,
                'term': meta.get('display_name', acid),
                'in_sapdt': meta.get('in_sapdt', 'No'),
                'in_vsct': meta.get('in_vsct', 'No'),
                'in_sct_inter': meta.get('in_sct_inter', 'Yes')
            })

        conn.close()

        # SCT-01 FIX: Build structured descriptions list (FSN / Preferred / Synonym / ku)
        # Follows SNOMED CT Browser description display standard
        descriptions = []

        # 1. FSN — Fully Specified Name
        fsn_val = main_row.get('snomed_fsn') or main_row.get('sapdt_fsn') or ''
        if fsn_val:
            descriptions.append({'type': 'FSN', 'lang': 'en', 'text': fsn_val})

        # 2. Preferred Term (skip if same as FSN)
        pt_val = main_row.get('snomed_preferred_term') or ''
        if pt_val and pt_val != fsn_val:
            descriptions.append({'type': 'Preferred', 'lang': 'en', 'text': pt_val})

        # 3. SNOMED all_synonyms (pipe-separated) from VSCT / SCT-Inter
        seen_texts = {fsn_val, pt_val}
        for r in master_rows:
            raw = r.get('snomed_all_synonyms') or ''
            for s in raw.split('|'):
                s = s.strip()
                if s and s not in seen_texts:
                    descriptions.append({'type': 'Synonym', 'lang': 'en', 'text': s})
                    seen_texts.add(s)

        # 4. ku custom synonyms — query ku_synonym_text table (processed first so ku badge is given priority)
        ku_entries = []
        try:
            cursor2 = get_db().cursor()
            cursor2.execute(
                "SELECT ku_synonym_text, lang_tag FROM ku_synonym_text WHERE concept_id = ? ORDER BY id",
                (concept_id,)
            )
            for krow in cursor2.fetchall():
                text = krow[0]
                tag  = krow[1] or 'ku'
                if text and text not in seen_texts:
                    descriptions.append({'type': 'ku', 'lang': tag, 'text': text})
                    seen_texts.add(text)
                    ku_entries.append(text)
        except Exception:
            pass  # table not yet created — skip silently

        # 5. SA-PDT synonyms (pipe-separated field: synonym)
        for r in master_rows:
            raw = r.get('synonym') or ''
            for s in raw.split('|'):
                s = s.strip()
                if s and s not in seen_texts:
                    descriptions.append({'type': 'Synonym', 'lang': 'en', 'text': s})
                    seen_texts.add(s)

        # Legacy flat list (kept for diagram compatibility)
        synonyms_flat = [d['text'] for d in descriptions if d['type'] in ('Preferred', 'Synonym')]

        self.send_json({
            'concept_id': concept_id,
            'sapdt_concept_id': main_row.get('sapdt_concept_id') or '',
            'snomed_concept_id': main_row.get('snomed_concept_id') or '',
            'display_name': main_row.get('display_name'),
            'snomed_fsn': main_row.get('snomed_fsn'),
            'snomed_preferred_term': main_row.get('snomed_preferred_term'),
            'sapdt_fsn': main_row.get('sapdt_fsn'),
            'snomed_semantic_type': main_row.get('snomed_semantic_type'),
            'snomed_definition_status': main_row.get('snomed_definition_status'),
            'body_system': main_row.get('body_system'),
            'in_sapdt': main_row.get('in_sapdt'),
            'in_vsct': main_row.get('in_vsct'),
            'in_sct_inter': main_row.get('in_sct_inter'),
            'master_rows': master_rows,
            'descriptions': descriptions,      # SCT-01: structured list
            'synonyms': synonyms_flat,         # legacy flat list
            'parents': parents,
            'children': children,
            'children_total_count': children_total_count,   # CONFLICT-03
            'attributes': attributes
        })

def run():
    if not os.path.exists(DB_FILE):
        gz_file = DB_FILE + '.gz'
        if not os.path.exists(gz_file):
            db_url = os.environ.get(
                "DB_DOWNLOAD_URL",
                "https://github.com/imnipon/kahis-terminology/releases/download/v1.0/terminology_search.db.gz"
            )
            print(f"[INFO] Database not found. Downloading from release URL: {db_url} ...")
            try:
                import urllib.request
                urllib.request.urlretrieve(db_url, gz_file)
                print(f"[INFO] Download completed: {os.path.getsize(gz_file)/(1024*1024):.1f} MB")
            except Exception as e:
                print(f"ERROR: Failed to download database from {db_url}: {e}")
                sys.exit(1)

        if os.path.exists(gz_file):
            print(f"[INFO] Unpacking database: {gz_file} -> {DB_FILE} ...")
            import gzip, shutil
            with gzip.open(gz_file, 'rb') as f_in:
                with open(DB_FILE, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            print("[INFO] Database unpacking completed successfully.")
        else:
            print(f"ERROR: Database file not found!")
            print(f"  Expected: {DB_FILE} or {gz_file}")
            sys.exit(1)

    versions = get_release_versions()
    socketserver.TCPServer.allow_reuse_address = True
    server_address = ('', PORT)
    httpd = socketserver.TCPServer(server_address, TerminologyHandler)
    print("==================================================")
    print(f"SA-PDT & SNOMED CT Veterinary Extension for KAHIS")
    print(f"Running at : http://localhost:{PORT}")
    print(f"App Dir    : {APP_DIR}")
    print(f"Database   : {DB_FILE}")
    print(f"Sources    : {versions['sapdt']} | {versions['vsct']} | {versions['sct']}")
    print("==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == '__main__':
    run()
