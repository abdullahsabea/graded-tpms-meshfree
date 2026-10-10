"""Replace superseded labels inside the legacy vector figures used by the
supplement. Each label is redacted (white fill) and rewritten at the same
position and size; any other text span removed as collateral damage by a
redaction box is restored at its original origin. Titles ('c') are
re-centred, legend/axis labels ('l') stay left-anchored.
Writes <name>_v7.pdf; originals are untouched."""
import pymupdf

JOBS = {
    "fig9_mesh_convergence.pdf": [("Optimized graded", "Unconstrained design", "l"),
                                  ("Constrained variant", "Band-restricted", "l")],
    "fig15_geometry.pdf": [("VG-MM winner", "Filtered search, seed 11", "c"),
                           ("Full-FE winner", "FE coordinate search", "c")],
    "fig10_experimental.pdf": [("Elastic-window fits", "Loading-window regressions", "l"),
                               ("constrained graded", "band-restricted graded", "c")],
}


def spans_of(page):
    return [s for b in page.get_text("dict")["blocks"] for l in b.get("lines", []) for s in l["spans"]
            if s["text"].strip()]


for fname, pairs in JOBS.items():
    doc = pymupdf.open(fname)
    page = doc[0]
    before = spans_of(page)
    todo, olds = [], [o.replace("SPAN:", "") for o, _, _ in pairs]
    for old, new, anchor in pairs:
        if old.startswith("SPAN:"):
            key = old[5:]
            for s in before:
                if key in s["text"]:
                    r = pymupdf.Rect(s["bbox"])
                    todo.append((r, new, s["size"], anchor))
                    page.add_redact_annot(r, fill=(1, 1, 1))
            continue
        for r in page.search_for(old):
            size = next((s["size"] for s in before if old.split()[0] in s["text"]
                         and pymupdf.Rect(s["bbox"]).intersects(r)), r.height * 0.8)
            todo.append((r, new, size, anchor))
            page.add_redact_annot(r, fill=(1, 1, 1))
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
    after_txt = [s["text"] for s in spans_of(page)]
    restored = 0
    for s in before:
        if s["text"] in after_txt or any(o in s["text"] for o in olds):
            continue
        page.insert_text(s["origin"], s["text"], fontname="tiro", fontsize=s["size"],
                         color=tuple(((s["color"] >> k) & 255) / 255 for k in (16, 8, 0)))
        restored += 1
    for r, new, size, anchor in todo:
        w = pymupdf.get_text_length(new, fontname="tiro", fontsize=size)
        x = (r.x0 + r.x1) / 2 - w / 2 if anchor == "c" else r.x0
        page.insert_text((x, r.y1 - 0.22 * r.height), new, fontname="tiro", fontsize=size, color=(0, 0, 0))
    out = fname.replace(".pdf", "_v7.pdf")
    doc.save(out)
    print("wrote", out, "| replaced", len(todo), "| restored collateral spans", restored)
