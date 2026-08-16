# 🏛️ ATHENA SYSTEM ARCHITECTURE & MASTER CHAT SESSION RESUME
> **Developer Note:** If this chat session ever expires, drops, or hits a browser refresh error, copy and paste this entire markdown file into the very first prompt of a new chat to instantly restore 100% of the AI's contextual memory.

---

## 📍 1. SYSTEM BASELINE & HARDWARE TOPOLOGY
*   **Host PC Target:** Local desktop machine in the workshop.
*   **Working Directory:** `D:\Athena`
*   **Remote Mobility Node:** Galaxy S25 Ultra running the **Parsec** native mobile application. 
*   **Connection Status:** Confirmed active, zero-lag visual streaming, and fully synchronized remote keyboard/mouse inputs from the watchbench.

---

## 🛠️ 2. THE CHRONOLOGICAL PIPELINE VOYAGE & BUG JOURNAL
This log details the barriers we broke through, preventing future regression:

### ❌ The Path & Module Execution Clashes
*   **The Issue:** Running `python vault_maintenance.py` from the root directory failed with path index errors because the master script lived nested inside `core/vault/`.
*   **The Solution:** Standardized the project root via `Path(__file__).resolve().parents[2]` and enforced module execution syntax: `python -m core.vault.vault_maintenance`.
*   **Duplicate Extermination:** Found a duplicate script copy sitting in the root folder that was muddying execution lanes; it was safely deleted.

### 📁 The Folder Identity Crisis (`vault` vs `documents`)
*   **The Issue:** The initial script flatlined with a fatal directory missing error because it was looking for `D:\Athena\vault`, while your true target data was hidden in a deeply nested sub-hierarchy under `athena_vault/Watchmaking files/Watchmaking/`.
*   **The Solution:** Ran a recursive PowerShell sweep string to cleanly copy every nested sub-directory's PDF guides into a flat, accessible data staging ground inside `D:\Athena\vault`.

### 🛑 The Cloud API Quota & SDK Barrier
*   **The Issue:** Attempted a cloud execution loop using `google-generativeai`. It repeatedly crashed with `404 API version v1beta` deprecated endpoint errors and split on a hard `429 Resource Exhausted` barrier after processing a tiny handful of documents due to a rigid 20 free requests/day daily limit.
*   **The Solution:** Transferred the backend hooks away from cloud endpoints entirely, shifting the framework onto an un-metered local hardware solution.

### 🦙 The Local Inference Engine & PDF Image Compilers
*   **The Issue:** Shifted to local hardware inference via **Ollama**. `llama3.2-vision` failed with an internal model server `mllama` architecture loading crash. Additionally, `pdf2image` broke with visual errors because the Windows host environment was missing the compiled system binaries for **Poppler**.
*   **The Solution:** 
    1. Swapped the model payload to **Moondream** via `ollama pull moondream`.
    2. Deployed **Poppler** natively onto the machine using `winget install oschwartz10612.poppler`.
    3. Added a dynamic self-sensing python function (`find_windows_poppler_path`) right into the script to automatically find where winget hid the binaries.

---

## 🚀 3. THE NEXT LOGICAL MILESTONES (WHERE WE GO NEXT)
Once this log is locked onto your drive, we will proceed down these architectural branches:

1.  **Transition to Paid Production Cloud API:** Update our script to point to an OpenAI API key or a stable production tier Google Cloud key to eliminate small local model text format errors and allow perfect watchmaker caliber classification.
2.  **Add Failed File Isolation Tracking:** Create a automatic `D:\Athena\vault\manual_sorting\` subdirectory where corrupted, hidden macOS system tracking files (`._0540.pdf`), or unparseable files are safely isolated without stalling the loop.
3.  **Build the Mobile Ingestion Portal:** Upgrade your main `athena_api.py` script to accept file streams via mobile web browser endpoints.
4.  **Inject the UI Interface:** Add an upload button onto your Galaxy S25 Ultra custom workbench web panel layout to support seamless mobile-to-PC file drops.
======================================================================
