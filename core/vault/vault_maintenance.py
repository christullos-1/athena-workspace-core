"""
Athena Vault Maintenance — Structure-Preserving One-for-One Copy
===============================================================
Purpose:
  Copy every PDF from the original source vault into D:\Athena\vault
  while keeping the exact relative folder structure intact.

  - No renaming
  - No reclassification into Interchangeability / Movements / etc.
  - No caliber folders
  - No automatic duplicate suffixing
  - Source files are never moved or deleted

  Safe to re-run: skips a destination file if it already exists and has the same size.

Usage:
  python core/vault/vault_maintenance.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (adjust if your layout differs)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path("D:/Athena")
SOURCE_DIR   = PROJECT_ROOT / "athena_vault" / "Watchmaking files"
DEST_DIR     = PROJECT_ROOT / "vault"


def copy_structure_preserving() -> None:
    print("=" * 70)
    print("Athena — Structure-Preserving One-for-One Copy")
    print("Source :", SOURCE_DIR)
    print("Dest   :", DEST_DIR)
    print("=" * 70)

    if not SOURCE_DIR.exists():
        print("ERROR: Source directory does not exist.")
        print(f"Expected: {SOURCE_DIR}")
        return

    DEST_DIR.mkdir(parents=True, exist_ok=True)

    all_pdfs = [
        f for f in SOURCE_DIR.rglob("*")
        if f.is_file() and f.suffix.lower() == ".pdf"
    ]

    print(f"Found {len(all_pdfs)} PDF files in source.\n")

    copied = 0
    skipped = 0
    errors = 0

    for src in all_pdfs:
        # Preserve exact relative path
        rel = src.relative_to(SOURCE_DIR)
        dest = DEST_DIR / rel

        dest.parent.mkdir(parents=True, exist_ok=True)

        # Skip if destination already exists with the same size
        if dest.exists():
            try:
                if dest.stat().st_size == src.stat().st_size:
                    print(f"SKIP (same size): {rel}")
                    skipped += 1
                    continue
            except Exception:
                pass

        try:
            shutil.copy2(src, dest)
            print(f"COPY: {rel}")
            copied += 1
        except Exception as e:
            print(f"ERROR copying {rel}: {e}")
            errors += 1

    print("\n" + "=" * 70)
    print(f"Done.")
    print(f"  Copied  : {copied}")
    print(f"  Skipped : {skipped}")
    print(f"  Errors  : {errors}")
    print(f"Destination: {DEST_DIR}")
    print("Original files were left completely untouched.")
    print("=" * 70)


if __name__ == "__main__":
    copy_structure_preserving()
