import os
import sys
import uvicorn
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

PROJECT_ROOT = Path("D:/Athena")
VAULT_DIR = PROJECT_ROOT / "vault"
STATIC_DIR = PROJECT_ROOT / "static"

app = FastAPI(title="Athena Horology Vault", version="2.0.0")

for path in [VAULT_DIR, STATIC_DIR]:
    path.mkdir(parents=True, exist_ok=True)

if any(STATIC_DIR.iterdir()):
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

FIXED_USERS = {
    "athena_admin": {"password": "YOUR_SECURE_ADMIN_PASSWORD", "role": "admin", "can_download": True},
    "tester_one": {"password": "PASSWORD_1", "role": "tester", "can_download": False},
    "tester_two": {"password": "PASSWORD_2", "role": "tester", "can_download": False},
    "tester_three": {"password": "PASSWORD_3", "role": "tester", "can_download": True}
}

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/login")
def login_user(payload: LoginRequest, request: Request):
    user = FIXED_USERS.get(payload.username)
    if not user or user["password"] != payload.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "status": "success",
        "role": user["role"],
        "can_download": user["can_download"],
        "logged_ip": request.client.host
    }

@app.get("/", response_class=HTMLResponse)
async def render_dashboard_interface():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🏛️ Athena Workstation</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #121212; color: #e0e0e0; margin: 0; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2d2d2d; padding-bottom: 20px; margin-bottom: 30px; }
            h1 { color: #ffffff; margin: 0; font-size: 24px; }
            .badge { background: #1a73e8; color: white; padding: 4px 12px; border-radius: 16px; font-size: 12px; font-weight: bold; }
            .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
            .card { background: #1e1e1e; border: 1px solid #2d2d2d; border-radius: 8px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: transform 0.2s; }
            .card:hover { transform: translateY(-2px); border-color: #404040; }
            .folder-title { font-size: 18px; font-weight: bold; color: #ffffff; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }
            .file-count { color: #888888; font-size: 14px; }
            .status-box { background: #1a1a1a; border-left: 4px solid #00e676; padding: 15px; margin-bottom: 30px; border-radius: 0 8px 8px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🏛️ ATHENA HOROLOGY VAULT PANEL</h1>
                <span class="badge">ADMIN MODE ACTIVE</span>
            </header>
            <div class="status-box">
                <strong>System Status:</strong> Local GPU pipeline actively restructuring database records in background.
            </div>
            <div class="grid">
                <div class="card">
                    <div class="folder-title">📁 Movements</div>
                    <p class="file-count">Subfolders systematically indexed by movement manufacturer tiers.</p>
                </div>
                <div class="card">
                    <div class="folder-title">🛠️ Admin Controls</div>
                    <p class="file-count">Fixed multi-user access rules and location tracing strings armed.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
