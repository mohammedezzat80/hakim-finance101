#!/usr/bin/env python3
"""HAKIM · Ledger export — CSV (full detail) + PDF (one-page summary).

Writes dated files to ~/Documents/Hakim/exports/. Read-only: pulls transactions
straight from Firefly (via _ff.py, stdlib only) and never writes back. The PDF is
hand-built (no external libs) so this runs on the host Python with no installs.

Run:  make export   (or:  python3 scripts/export_ledger.py)
"""
import csv
import os
from datetime import datetime

from _ff import Firefly, load_env

OUT_DIR = os.path.expanduser("~/Documents/Hakim/exports")
STAMP = datetime.now().strftime("%Y-%m-%d")


def fetch_rows():
    ff = Firefly(load_env())
    rows = []
    for g in ff.get_all("transactions"):
        for s in g["attributes"]["transactions"]:
            rows.append({
                "date": (s.get("date") or "")[:10],
                "type": s.get("type"),
                "amount": s.get("amount"),
                "currency": s.get("currency_code"),
                "source": s.get("source_name"),
                "destination": s.get("destination_name"),
                "category": s.get("category_name") or "",
                "description": s.get("description") or "",
                "notes": (s.get("notes") or "").replace("\n", " "),
                "tags": ", ".join(s.get("tags") or []),
            })
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows


def write_csv(rows, path):
    cols = ["date", "type", "amount", "currency", "source", "destination",
            "category", "description", "notes", "tags"]
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def _pdf_escape(s):
    # Helvetica base font is ASCII-only; keep the PDF honest and legible.
    s = "".join(c if 32 <= ord(c) < 127 else "?" for c in str(s))
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def write_summary_pdf(rows, path):
    n = len(rows)
    tin = sum(float(r["amount"]) for r in rows if r["type"] == "deposit")
    tout = sum(float(r["amount"]) for r in rows if r["type"] == "withdrawal")
    catmap = {}
    for r in rows:
        if r["type"] != "withdrawal":
            continue
        c = (r["category"] or "Uncategorized").split(":")[0].strip() or "Uncategorized"
        catmap[c] = catmap.get(c, 0.0) + float(r["amount"])
    top = sorted(catmap.items(), key=lambda x: -x[1])[:10]

    lines = [("HAKIM . Finance -- Ledger Summary", 18),
             (f"Generated: {STAMP}", 10),
             ("", 6),
             (f"Transactions: {n:,}", 12),
             (f"Total in:  SAR {tin:,.2f}", 12),
             (f"Total out: SAR {tout:,.2f}", 12),
             (f"Net:       SAR {tin - tout:,.2f}", 12),
             ("", 6),
             ("Top spending categories:", 12)]
    for name, amt in top:
        lines.append((f"   {name[:38]:<40} SAR {amt:,.2f}", 10))
    lines += [("", 8),
              ("Full transaction detail is in the accompanying CSV.", 9),
              ("Read-only export. HAKIM Finance -- personal ledger only.", 9)]

    # content stream: absolute text-matrix position per line (simple + robust)
    content = "BT\n"
    y = 800
    for text, size in lines:
        y -= size + 6
        content += f"/F1 {size} Tf 1 0 0 1 50 {y} Tm ({_pdf_escape(text)}) Tj\n"
    content += "ET"
    cbytes = content.encode("latin-1")

    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(cbytes)).encode() + b" >>\nstream\n" + cbytes + b"\nendstream",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n").encode()
    with open(path, "wb") as fh:
        fh.write(out)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = fetch_rows()
    csv_path = os.path.join(OUT_DIR, f"hakim-ledger-{STAMP}.csv")
    pdf_path = os.path.join(OUT_DIR, f"hakim-summary-{STAMP}.pdf")
    write_csv(rows, csv_path)
    write_summary_pdf(rows, pdf_path)
    print(f"exported {len(rows)} transactions")
    print(f"  CSV: {csv_path}")
    print(f"  PDF: {pdf_path}")


if __name__ == "__main__":
    main()
