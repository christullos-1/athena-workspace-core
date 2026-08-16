$p1 = @'
import os
import re
from pathlib import Path
import pypdf

PROJECT_ROOT = Path("D:/Athena")
STAGING_DIR = PROJECT_ROOT / "athena_vault" / "Watchmaking files" 
VAULT_DIR = PROJECT_ROOT / "vault"
STAGING_CACHE = PROJECT_ROOT / "staging_cache"
LOCAL_MODEL = "llava"

REFERENCE_KEYWORDS = [
    r"\bbook\b", r"encyclopedia", r"history", r"society", r"treatise", 
    r"textbook", r"journal", r"magazine", r"bulletin", r"horology", 
    r"clocks", r"escapement", r"annual_report", r"proceedings", r"dictionary"
]

INTERCHANGEABILITY_KEYWORDS = [
    r"interchange", r"interchangability", r"interchangeability", r"cross_reference", 
    r"cross-reference", r"cross reference", r"inter_change", r"parts_crossing", 
    r"staff_fit", r"staff fit", r"material_cross", r"retrofit"
]

KNOWN_BRANDS = [
    "seiko", "omega", "bulova", "citizen", "eta", "rolex", "longines", "tissot", 
    "hamilton", "tudor", "zenith", "zodiac", "valjoux", "venus", "sellita", "soprod",
    "peseux", "poljot", "oris", "movado", "lemania", "luch", "landeron", "iwc", "jlc",
    "heuer", "felsa", "fef", "eterna", "enicar", "elgin", "election", "ebosa", "eb", 
    "esa", "cyma", "cortebert", "certina", "cartier", "cattin", "chaika", "buren", 
    "buser", "agat", "arogno", "bfg", "bestfit", "av", "as", "af"
]

CALIBER_PATTERNS = [
    r"\bcal(?:iber|ibre)?\.?\s*([a-zA-Z0-9_\-]+)\b",
    r"\bmov(?:t|ement)?\.?\s*([a-zA-Z0-9_\-]+)\b",
    r"\bref\.?\s*([a-zA-Z0-9_\-]+)\b",
    r"\b(?<!\d)(\d{4}[A-Z0-9]?|[A-Z0-9]{2,4}\d{2,4}[A-Z0-9]?)\b"
]

def clean_file_string(text_string: str) -> str:
    text_string = text_string.encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[\/*?:"<>|]', "", text_string).strip().replace(" ", "_")
'@ | Out-File -FilePath "D:\Athena\core\vault\vault_maintenance_part1.py" -Encoding utf8
$p2 = @'
import os
import sys
import json
import re
import shutil
from pathlib import Path
import ollama
from pdf2image import convert_from_path

# Bind to Part 1 metrics
sys.path.insert(0, str(Path("D:/Athena/core/vault")))
import vault_maintenance_part1 as p1

def find_windows_poppler_path() -> str:
    possible_roots = [
        Path(os.environ.get("LOCALAPPDATA", "")),
        Path("C:/Program Files"),
        Path("C:/poppler")
    ]
    for root in possible_roots:
        if not root or not root.exists(): continue
        for match in root.glob("**/pdfinfo.exe"): return str(match.parent)
    return None

def inspect_pdf_structure(file_path: Path) -> tuple:
    try:
        import pypdf
        reader = pypdf.PdfReader(file_path)
        total_pages = len(reader.pages)
        text_accumulator = []
        for page_idx in range(min(5, total_pages)):
            text_accumulator.append(reader.pages[page_idx].extract_text() or "")
        return total_pages, " ".join(text_accumulator), file_path.name
    except Exception:
        return 1, "" , file_path.name

def is_interchangeability_document(filename: str, sample_text: str) -> bool:
    combined_lower = (filename + " " + sample_text).lower()
    return any(re.search(pat, combined_lower) for pat in p1.INTERCHANGEABILITY_KEYWORDS)

def is_explicit_reference_book(filename: str, sample_text: str, total_pages: int, has_caliber: bool) -> bool:
    if total_pages > 60:
        return True
    combined_lower = (filename + " " + sample_text).lower()
    if any(re.search(pat, combined_lower) for pat in p1.REFERENCE_KEYWORDS) and not has_caliber:
        return True
    return False

def extract_caliber_signature(filename: str, sample_text: str) -> str:
    combined = (filename + " " + sample_text).lower()
    for pattern in p1.CALIBER_PATTERNS:
        match = re.search(pattern, combined)
        if match:
            extracted = match.group(1) if match.groups() else match.group(0)
            if len(extracted) > 1 and not extracted.isdigit() and len(extracted) < 12:
                return p1.clean_file_string(extracted).upper()
            elif extracted.isdigit() and len(extracted) >= 3 and len(extracted) <= 5:
                return p1.clean_file_string(extracted).upper()
    return None

def scan_text_for_known_brand(filename: str, sample_text: str) -> str:
    combined_target = (filename + " " + sample_text).lower()
    for brand in p1.KNOWN_BRANDS:
        if len(brand) <= 2:
            pattern = r'(?<![a-zA-Z])' + brand + r'(?:\s+\d+|\b)'
            if brand == "as" and not re.search(r'\bas\s+\d+', combined_target) and brand not in filename.lower():
                continue
        else:
            pattern = r'\b' + brand + r'\b'
        if re.search(pattern, combined_target):
            return brand.upper() if len(brand) <= 3 else brand.capitalize()
    return None

def parse_model_response(raw_text: str, fallback_name: str, preset_brand: str = None) -> dict:
    default_brand = preset_brand if preset_brand else "Unknown_Brand"
    try:
        clean_str = re.sub(r"```json\s*|\s*```", "", raw_text.strip())
        data = json.loads(clean_str)
        if data.get("true_title") and data["true_title"] != "Unknown":
            if not data.get("manufacturer") or data["manufacturer"] == "Unknown_Brand":
                data["manufacturer"] = default_brand
            return data
    except Exception:
        pass
    base_clean = Path(fallback_name).stem.replace("-", "_").replace(" ", "_")
    return {"manufacturer": default_brand, "true_title": base_clean, "year": "Unknown", "era": "vintage"}

def process_movement_via_gpu_vision(file_path: Path, preset_brand: str = None) -> dict:
    try:
        poppler_bin = find_windows_poppler_path()
        pages = convert_from_path(str(file_path), first_page=1, last_page=10, poppler_path=poppler_bin)
        if not pages: return parse_model_response("", file_path.name, preset_brand)
        p1.STAGING_CACHE.mkdir(parents=True, exist_ok=True)
        temp_img_path = p1.STAGING_CACHE / f"{file_path.stem}_eval.jpg"
        target_page = pages
        for p_idx, page in enumerate(pages):
            if p_idx < 2 and len(pages) > 2: continue
            target_page = page
            break
        target_page.save(temp_img_path, "JPEG")
        vision_prompt = (
            "Analyze this technical watch schematic page image. "
            "Identify the brand manufacturer name (e.g., Omega, Seiko, Bulova, Citizen, ETA) into 'manufacturer'. "
            "Identify the exact caliber reference identifier number into 'true_title'. "
            "Respond strictly with a clean JSON object: {'manufacturer': '...', 'true_title': '...', 'year': '...', 'era': '...'}"
        )
        res = ollama.chat(model=p1.LOCAL_MODEL, messages=[{ 'role': 'user', 'content': vision_prompt, 'images': [str(temp_img_path)] }])
        if temp_img_path.exists(): temp_img_path.unlink()
        return parse_model_response(res['message']['content'], file_path.name, preset_brand)
    except Exception as e:
        print(f"[GPU Vision Error] {e}")
        return parse_model_response("", file_path.name, preset_brand)

def execute_batch_grouping_pipeline():
    print(f"[Pipeline Ingestion] Direct target sync sweeping across: {p1.STAGING_DIR}")
    p1.VAULT_DIR.mkdir(parents=True, exist_ok=True)
    all_files = [f for f in p1.STAGING_DIR.rglob("*") if f.is_file() and f.suffix.lower() == ".pdf" and "vault" not in f.parts]
    if not all_files:
        print("Zero target documents located.")
        return
    print(f"Constructing profiles map for {len(all_files)} total matching files...")
    file_profiles = []
    caliber_groups = {}
    for idx, file_path in enumerate(all_files, 1):
        total_pages, raw_text, filename = inspect_pdf_structure(file_path)
        detected_brand = scan_text_for_known_brand(filename, raw_text)
        detected_caliber = extract_caliber_signature(filename, raw_text)
        is_interchange = is_interchangeability_document(filename, raw_text)
        is_book = False
        if not is_interchange:
            if total_pages > 60:
                is_book = True
            else:
                combined_lower = (filename + " " + raw_text).lower()
                if any(re.search(pat, combined_lower) for pat in p1.REFERENCE_KEYWORDS) and not detected_caliber:
                    is_book = True
        profile = {
            "path": file_path, "total_pages": total_pages, "raw_text": raw_text,
            "brand": detected_brand, "caliber": detected_caliber,
            "is_interchange": is_interchange, "is_book": is_book
        }
        file_profiles.append(profile)
        if detected_caliber and not is_book and not is_interchange:
            caliber_groups[detected_caliber] = caliber_groups.get(detected_caliber, 0) + 1

    print("\nProfiles built. Executing high-intelligence contextual restructuring...")
    for idx, profile in enumerate(file_profiles, 1):
        file_path = profile["path"]
        print(f"\nProcessing File [{idx}/{len(file_profiles)}]: {file_path.name}")
        if profile["is_interchange"]:
            print(" -> Context Profile: Interchangeability guide. Routing to Interchangeability hub.")
            target_folder = p1.VAULT_DIR / "Interchangeability"
            target_folder.mkdir(parents=True, exist_ok=True)
            new_name = f"vintage_{p1.clean_file_string(file_path.stem)}_Interchange.pdf"
            new_path = target_folder / new_name
        elif profile["is_book"]:
            print(" -> Context Profile: Horology Publication volume. Routing to Reference Library.")
            target_folder = p1.VAULT_DIR / "Reference_Library"
            target_folder.mkdir(parents=True, exist_ok=True)
            new_name = f"vintage_{p1.clean_file_string(file_path.stem)}_Publication.pdf"
            new_path = target_folder / new_name
        else:
            if not profile["brand"] or not profile["caliber"]:
                metadata = process_movement_via_gpu_vision(file_path, preset_brand=profile["brand"])
                brand = profile["brand"] if profile["brand"] else metadata.get("manufacturer", "Unknown_Brand")
                caliber = profile["caliber"] if profile["caliber"] else metadata.get("true_title", "Unknown")
            else:
                brand = profile["brand"]
                caliber = profile["caliber"]
            clean_mfg = p1.clean_file_string(brand).upper() if len(brand) <= 3 else p1.clean_file_string(brand).capitalize()
            clean_cal = p1.clean_file_string(caliber).upper()
            if caliber_groups.get(caliber, 0) > 1 and clean_cal != "UNKNOWN":
                target_folder = p1.VAULT_DIR / "Movements" / clean_mfg / f"Caliber_{clean_cal}"
                print(f" -> Group Trigger: Multiple documents found for Caliber {clean_cal}. Creating dynamic bundle folder.")
            else:
                target_folder = p1.VAULT_DIR / "Movements" / clean_mfg
            target_folder.mkdir(parents=True, exist_ok=True)
            new_name = f"vintage_{clean_mfg}_{clean_cal}.pdf"
            new_path = target_folder / new_name
        if new_path.exists() and new_path != file_path:
            new_name = f"{Path(new_name).stem}_{idx}.pdf"
            new_path = target_folder / new_name
        try:
            shutil.copy2(str(file_path), str(new_path))
            print(f"[Success] Structured into: vault/{target_folder.relative_to(p1.VAULT_DIR)}\\{new_name}")
        except Exception as e:
            print(f"[Disk Warning]: {e}")

if __name__ == "__main__":
    execute_batch_grouping_pipeline()
'@ | Out-File -FilePath "D:\Athena\core\vault\vault_maintenance_part2.py" -Encoding utf8
