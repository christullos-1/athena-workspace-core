"""
Athena Vault Maintenance — Duplicate Report Tool
================================================
Purpose:
  Scan the ORIGINAL source vault and produce a clear text report of
  near-duplicate PDF groups. No files are copied, moved, or deleted.

Duplicate criteria:
  - Same filename stem
  - Same file size
  - Same page count
  - Very similar text from the first 5 pages

Report is written to:
  D:\Athena\vault\duplicate_report.txt
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path("D:/Athena")
SOURCE_DIR   = PROJECT_ROOT / "athena_vault" / "Watchmaking files"
REPORT_DIR   = PROJECT_ROOT / "vault"
REPORT_FILE  = REPORT_DIR / "duplicate_report.txt"


def get_pdf_fingerprint(file_path: Path) -> tuple[int, int, str]:
    """Return (file_size, page_count, normalised first-5-pages text)."""
    try:
        import pypdf
        size = file_path.stat().st_size
        reader = pypdf.PdfReader(str(file_path))
        pages = len(reader.pages)
        text_parts = []
        for i in range(min(5, pages)):
            text_parts.append(reader.pages[i].extract_text() or "")
        sample = " ".join(text_parts)
        sample = re.sub(r"\s+", " ", sample).strip().lower()[:2000]
        return size, pages, sample
    except Exception:
        try:
            return file_path.stat().st_size, 0, ""
        except Exception:
            return 0, 0, ""


def is_near_duplicate(fp1: tuple, fp2: tuple) -> bool:
    """Same size + same page count + highly similar first-page text."""
    size1, pages1, text1 = fp1
    size2, pages2, text2 = fp2

    if size1 != size2 or pages1 != pages2:
        return False

    if not text1 or not text2:
        # Fall back to size + page count only when text extraction fails
        return True

    if text1[:300] == text2[:300]:
        return True

    words1 = set(text1.split())
    words2 = set(text2.split())
    if not words1 or not words2:
        return False

    overlap = len(words1 & words2) / max(len(words1), len(words2))
    return overlap > 0.85


def run_duplicate_report() -> None:
    print("=" * 70)
    print("Athena — Duplicate Report Tool")
    print("Source :", SOURCE_DIR)
    print("Report :", REPORT_FILE)
    print("=" * 70)

    if not SOURCE_DIR.exists():
        print("ERROR: Source directory does not exist.")
        return

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    all_pdfs = [
        f for f in SOURCE_DIR.rglob("*")
        if f.is_file() and f.suffix.lower() == ".pdf"
    ]
    print(f"Found {len(all_pdfs)} PDF files.\n")

    # Group by filename stem (fast pre-filter)
    by_stem: dict[str, list[Path]] = defaultdict(list)
    for pdf in all_pdfs:
        by_stem[pdf.stem.lower()].append(pdf)

    duplicate_groups: list[list[Path]] = []
    unique_count = 0

    print("Scanning for near-duplicates...\n")

    for stem, candidates in sorted(by_stem.items()):
        if len(candidates) == 1:
            unique_count += 1
            continue

        # Build fingerprints
        fingerprints = [(path, get_pdf_fingerprint(path)) for path in candidates]

        # Cluster into near-duplicate groups
        clusters: list[list[tuple[Path, tuple]]] = []

        for path, fp in fingerprints:
            placed = False
            for cluster in clusters:
                # Compare against the first member of the cluster
                if is_near_duplicate(fp, cluster[0][1]):
                    cluster.append((path, fp))
                    placed = True
                    break
            if not placed:
                clusters.append([(path, fp)])

        for cluster in clusters:
            if len(cluster) > 1:
                duplicate_groups.append([item[0] for item in cluster])
            else:
                unique_count += 1

    # Write the report
    lines = []
    lines.append("ATHENA DUPLICATE REPORT")
    lines.append(f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Source    : {SOURCE_DIR}")
    lines.append(f"Total PDFs scanned : {len(all_pdfs)}")
    lines.append(f"Unique documents   : {unique_count}")
    lines.append(f"Duplicate groups   : {len(duplicate_groups)}")
    lines.append("=" * 70)
    lines.append("")

    if not duplicate_groups:
        lines.append("No near-duplicates found.")
    else:
        for i, group in enumerate(sorted(duplicate_groups, key=lambda g: g[0].name.lower()), 1):
            # Get size & pages from the first file for the header
            size, pages, _ = get_pdf_fingerprint(group[0])
            lines.append(f"GROUP {i:03d}  |  {len(group)} copies  |  "
                         f"Size: {size:,} bytes  |  Pages: {pages}")
            lines.append("-" * 70)
            for path in sorted(group, key=lambda p: str(p).lower()):
                lines.append(f"  {path}")
            lines.append("")

    report_text = "\n".join(lines)

    REPORT_FILE.write_text(report_text, encoding="utf-8")

    print(report_text)
    print("=" * 70)
    print(f"Report saved to: {REPORT_FILE}")
    print("No files were copied, moved, or deleted.")
    print("=" * 70)


if __name__ == "__main__":
    run_duplicate_report()
