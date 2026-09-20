import csv
import re
from pathlib import Path

D = Path("data/shopee")
REQ = ["doc_id", "title", "source_url", "retrieved_at", "document_version", "audience"]

mds = sorted(D.glob("*.md"))
sources_path = D / "sources.csv"
rows = list(csv.DictReader(open(sources_path, encoding="utf-8"))) if sources_path.exists() else []

ids, auds = [], {}
for p in mds:
    content = p.read_text(encoding="utf-8")
    fm = {}
    if "---" in content:
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_lines = re.findall(r'^(\w+):\s*"?([^"\n]+)"?$', parts[1], re.M)
            fm = dict(fm_lines)
    
    doc_id = fm.get("doc_id")
    ids.append(doc_id)
    aud = fm.get("audience")
    if aud:
        auds[aud] = auds.get(aud, 0) + 1
    
    ok = all(k in fm for k in REQ) and doc_id == p.stem
    print(f"{p.name:42} {'OK' if ok else 'THIEU METADATA'}")

print("so file :", len(mds), "(can 5-10)")
print("csv     :", "khop" if sorted(r["doc_id"] for r in rows) == sorted(ids) else "LECH")
print("audience:", auds)
