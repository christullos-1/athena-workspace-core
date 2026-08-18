"""
Athena Vault Maintenance — Deduplicate + Reference Copy Tool
=============================================================
Purpose (August 2026):
  Scan the ORIGINAL source vault, detect near-duplicates, and place
  ONE clean copy of each unique document into the structured vault.

  Duplicate criteria (user-defined):
    - Same filename (stem)
    - Same file size
    - Same page count
    - Same / very similar text from the first 5 pages

  Original files are NEVER moved or deleted.
  This gives you a clean reference set so you can safely delete
  extra copies while going through the original list.
"""

from __future__ import annotations

import hashlib
import re
import shutil
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path("D:/Athena")
SOURCE_DIR   = PROJECT_ROOT / "athena_vault" / "Watchmaking files"   # original files
VAULT_DIR    = PROJECT_ROOT / "vault"                               # clean reference copies

# ---------------------------------------------------------------------------
# Classification helpers (kept simple for this focused tool)
# ---------------------------------------------------------------------------
REFERENCE_KEYWORDS = [
    r"\bbook\b", r"encyclopedia", r"history", r"society", r"treatise",
    r"textbook", r"journal", r"magazine", r"bulletin", r"horology",
    r"clocks", r"escapement", r"annual_report", r"proceedings", r"dictionary",
    r"lesson", r"course", r"school", r"manual", r"guideline", r"repair",
]

INTERCHANGEABILITY_KEYWORDS = [
    r"interchange", r"interchangability", r"interchangeability", r"cross_reference",
    r"cross-reference", r"cross reference", r"inter_change", r"parts_crossing",
    r"staff_fit", r"staff fit", r"material_cross", r"retrofit", r"parts catalog",
]

KNOWN_BRANDS = [
    "seiko", "omega", "bulova", "citizen", "eta", "rolex", "longines", "tissot",
    "hamilton", "tudor", "zenith", "zodiac", "valjoux", "venus", "sellita", "soprod",
    "peseux", "poljot", "oris", "movado", "lemania", "luch", "landeron", "iwc", "jlc",
    "heuer", "felsa", "fef", "eterna", "enicar", "elgin", "election", "ebosa", "eb",
    "esa", "cyma", "cortebert", "certina", "cartier", "cattin", "chaika", "buren",
    "buser", "agat", "arogno", "bfg", "bestfit", "av", "as", "af", "accutron",
    "accuquartz", "greiner", "vibrograf",
]


def clean_name(text: str) -> str:
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r'[\/*?:"<>|]', "", text).strip().replace(" ", "_")


def get_pdf_fingerprint(file_path: Path) -> tuple[int, int, str]:
    """Return (file_size, page_count, first_5_pages_text)."""
    try:
        import pypdf
        size = file_path.stat().st_size
        reader = pypdf.PdfReader(str(file_path))
        pages = len(reader.pages)
        text_parts = []
        for i in range(min(5, pages)):
            text_parts.append(reader.pages[i].extract_text() or "")
        sample = " ".join(text_parts)
        # Normalise whitespace for comparison
        sample = re.sub(r"\s+", " ", sample).strip().lower()[:2000]  # first ~2k chars is enough
        return size, pages, sample
    except Exception:
        return file_path.stat().st_size, 0, ""


def is_near_duplicate(fp1: tuple, fp2: tuple) -> bool:
    """Same size + same page count + highly similar first-page text."""
    size1, pages1, text1 = fp1
    size2, pages2, text2 = fp2
    if size1 != size2 or pages1 != pages2:
        return False
    if not text1 or not text2:
        return size1 == size2 and pages1 == pages2  # fall back to size+pages only
    # Simple similarity: shared prefix length or Jaccard on words
    if text1[:300] == text2[:300]:
        return True
    words1 = set(text1.split())
    words2 = set(text2.split())
    if not words1 or not words2:
        return False
    overlap = len(words1 & words2) / max(len(words1), len(words2))
    return overlap > 0.85


def classify_document(filename: str, sample_text: str, page_count: int) -> str:
    """Return top-level category: Interchangeability | Reference_Library | Movements."""
    combined = (filename + " " + sample_text).lower()

    if any(re.search(pat, combined) for pat in INTERCHANGEABILITY_KEYWORDS):
        return "Interchangeability"

    if page_count > 40 or any(re.search(pat, combined) for pat in REFERENCE_KEYWORDS):
        return "Reference_Library"

    return "Movements"


def detect_brand(filename: str, sample_text: str) -> str:
    combined = (filename + " " + sample_text).lower()
    for brand in KNOWN_BRANDS:
        if len(brand) <= 2:
            pattern = r"(?<![a-zA-Z])" + re.escape(brand) + r"(?:\s+\d+|\b)"
        else:
            pattern = r"\b" + re.escape(brand) + r"\b"
        if re.search(pattern, combined):
            return brand.upper() if len(brand) <= 3 else brand.capitalize()
    return "Unknown_Brand"


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------
def run_deduplicate_and_copy() -> None:
    print("=" * 70)
    print("Athena — Deduplicate + Reference Copy")
    print("Source :", SOURCE_DIR)
    print("Target :", VAULT_DIR)
    print("=" * 70)

    if not SOURCE_DIR.exists():
        print("ERROR: Source directory does not exist.")
        return

    VAULT_DIR.mkdir(parents=True, exist_ok=True)

    # Collect every PDF from the original vault
    all_pdfs = [
        f for f in SOURCE_DIR.rglob("*")
        if f.is_file() and f.suffix.lower() == ".pdf"
    ]
    print(f"Found {len(all_pdfs)} PDF files in source vault.\n")

    # Group by filename stem first (fast pre-filter)
    by_stem: dict[str, list[Path]] = defaultdict(list)
    for pdf in all_pdfs:
        by_stem[pdf.stem.lower()].append(pdf)

    unique_representatives: list[Path] = []
    duplicate_count = 0

    print("Scanning for near-duplicates (size + pages + first-5-pages text)...\n")

    for stem, candidates in by_stem.items():
        if len(candidates) == 1:
            unique_representatives.append(candidates[0])
            continue

        # Multiple files with same stem → deeper comparison
        fingerprints = []
        for path in candidates:
            fp = get_pdf_fingerprint(path)
            fingerprints.append((path, fp))

        kept = []
        for path, fp in fingerprints:
            is_dup = False
            for kept_path, kept_fp in kept:
                if is_near_duplicate(fp, kept_fp):
                    is_dup = True
                    duplicate_count += 1
                    print(f"  DUPLICATE of {kept_path.name}: {path.name}")
                    break
            if not is_dup:
                kept.append((path, fp))

        for path, _ in kept:
            unique_representatives.append(path)

    print(f"\nUnique documents to copy : {len(unique_representatives)}")
    print(f"Duplicates skipped       : {duplicate_count}\n")

    # Copy one clean version of each unique document
    print("Copying unique files into structured vault...\n")

    for idx, src in enumerate(unique_representatives, 1):
        size, pages, sample = get_pdf_fingerprint(src)
        category = classify_document(src.name, sample, pages)
        brand = detect_brand(src.name, sample)

        if category == "Interchangeability":
            target_folder = VAULT_DIR / "Interchangeability"
            new_name = f"{clean_name(src.stem)}_Interchange.pdf"
        elif category == "Reference_Library":
            target_folder = VAULT_DIR / "Reference_Library"
            # Preserve original parent folder name if meaningful
            parent_name = clean_name(src.parent.name) if src.parent != SOURCE_DIR else "General"
            target_folder = target_folder / parent_name
            new_name = f"{clean_name(src.stem)}.pdf"
        else:  # Movements
            target_folder = VAULT_DIR / "Movements" / brand
            new_name = f"{clean_name(src.stem)}.pdf"

        target_folder.mkdir(parents=True, exist_ok=True)
        dest = target_folder / new_name

        # Final safety: never overwrite an existing clean copy
        if dest.exists():
            dest = target_folder / f"{dest.stem}_{idx}.pdf"

        try:
            shutil.copy2(src, dest)
            print(f"[{idx:4d}/{len(unique_representatives)}] {src.name}")
            print(f"         → {dest.relative_to(VAULT_DIR)}")
        except Exception as e:
            print(f"  ERROR copying {src.name}: {e}")

    print("\n" + "=" * 70)
    print("Done.")
    print(f"Clean reference copies are in: {VAULT_DIR}")
    print("Original files were left completely untouched.")
    print("You can now use this clean set as your reference while manually")
    print("deleting extra copies from the original vault.")
    print("=" * 70)


if __name__ == "__main__":
    run_deduplicate_and_copy()
