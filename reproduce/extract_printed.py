"""Extract the printed table cells of the article and supplement LaTeX sources
into printed_tables.json (used by check_tables.py).

Usage: python extract_printed.py <manuscript.tex> <supplement.tex>
"""
import json
import re
import sys
from pathlib import Path

out = {}
for fn in sys.argv[1:3]:
    s = Path(fn).read_text(encoding="utf-8")
    for m in re.finditer(r"\\begin\{table\*?\}.*?\\end\{table\*?\}", s, re.S):
        b = m.group(0)
        lab = re.search(r"\\label\{([^}]*)\}", b).group(1)
        body = re.search(r"\\toprule(.*?)\\bottomrule", b, re.S)
        if not body:
            continue
        rows = []
        for r in re.split(r"\\\\(?:\[[^\]]*\])?", body.group(1)):
            r = re.sub(r"\\(midrule|cmidrule(\([^)]*\))?\{[^}]*\}|addlinespace)", "", r).strip()
            if not r:
                continue
            rows.append([c.strip() for c in r.split("&")])
        out[lab] = rows
Path(__file__).with_name("printed_tables.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
print({k: len(v) for k, v in out.items()})
