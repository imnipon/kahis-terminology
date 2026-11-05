import sys
import os

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# 1. Test release versions
vers = server.get_release_versions()
print("Release versions:", vers)
assert vers['sapdt'] != "SA-PDT N/A", "sapdt version should not be N/A"
assert vers['vsct'] != "VSCT N/A", "vsct version should not be N/A"
assert vers['sct'] != "SCT N/A", "sct version should not be N/A"

# 2. Test search API logic for 'นิ่ว'
class MockHandler:
    def __init__(self):
        self.result = None
    def send_json(self, data, status=200):
        self.result = data

h = MockHandler()
server.TerminologyHandler.handle_api_search(h, {'q': ['นิ่ว'], 'limit': ['10'], 'offset': ['0']})
print("Search result total:", h.result['total'])
print("Semantic counts:", h.result['semantic_counts'])
assert h.result['total'] == 5, f"Expected 5, got {h.result['total']}"
assert h.result['semantic_counts'].get('disorder') == 5, f"Expected disorder count 5, got {h.result['semantic_counts']}"
print("VERIFICATION SUCCESS: Search bug is completely FIXED!")
