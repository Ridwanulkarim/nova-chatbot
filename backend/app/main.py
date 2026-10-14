import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
import app.database.base  # Register all models with Base
from app.api.v1.api_router import api_router

# Schema initialization is intentionally decoupled from app import/startup
# to prevent DDL catalog lock contention on serverless cold starts.
# To initialize schema explicitly, run: python -m app.database.init_db

# Ensure upload directory exists safely
try:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
except Exception:
    pass

app = FastAPI(
    title="Pluto AI API",
    description="Backend API for Pluto AI conversational platform featuring streaming, RAG, and multi-provider intelligence.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware - Restrict strictly to configured CORS origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Secure file serving for uploads preventing stored XSS
@app.get("/uploads/{file_name:path}")
async def serve_upload(file_name: str):
    clean_name = os.path.basename(file_name)
    file_path = os.path.join(settings.UPLOAD_DIR, clean_name)
    if not os.path.exists(file_path):
        import tempfile
        tmp_path = os.path.join(tempfile.gettempdir(), clean_name)
        if os.path.exists(tmp_path):
            file_path = tmp_path
        else:
            return JSONResponse(status_code=404, content={"detail": "File not found"})

    ext = os.path.splitext(clean_name)[1].lower()
    # Explicitly block HTML, HTM, SVG, and script execution in browser origin
    disallowed_inline = {".html", ".htm", ".svg", ".xhtml", ".js", ".mjs", ".exe", ".sh", ".bat", ".php"}
    if ext in disallowed_inline:
        return JSONResponse(
            status_code=403,
            content={"detail": "Access restricted: potentially executable file types cannot be served."}
        )

    import mimetypes
    mime, _ = mimetypes.guess_type(file_path)
    if not mime:
        mime = "application/octet-stream"

    is_safe_image = ext in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".ico"}
    headers = {
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
    }
    if not is_safe_image:
        headers["Content-Disposition"] = f'attachment; filename="{clean_name}"'

    return FileResponse(file_path, media_type=mime, headers=headers)

# Mount API routes with all prefixes for seamless reverse proxy / Vercel compatibility
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router, prefix="/v1")
app.include_router(api_router, prefix="/api")
app.include_router(api_router)

# Determine Frontend Dist path
FRONTEND_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))
FRONTEND_ASSETS = os.path.join(FRONTEND_DIST, "assets")

if os.path.exists(FRONTEND_ASSETS):
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS), name="assets")

@app.get("/")
async def serve_root():
    index_file = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse(
        """
        <html>
            <head><title>Pluto AI</title></head>
            <body style="font-family: system-ui, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 90vh; background: #faf5ff; color: #1e1b4b;">
                <div style="background: white; padding: 2.5rem; border-radius: 1.5rem; box-shadow: 0 10px 25px rgba(168, 85, 247, 0.15); border: 1px solid #e9d5ff; max-width: 500px; text-align: center;">
                    <h1 style="margin: 0 0 0.5rem 0; font-size: 1.75rem;">✨ Pluto AI System</h1>
                    <p style="color: #6b7280; margin-bottom: 1.5rem; font-size: 0.95rem;">Backend API is fully operational.</p>
                    <a href="http://localhost:5180" style="display: inline-block; background: #9333ea; color: white; padding: 0.75rem 1.5rem; border-radius: 0.75rem; text-decoration: none; font-weight: 600; margin-bottom: 0.75rem;">
                        Open Chatbot UI (Port 5180) &rarr;
                    </a>
                    <br/>
                    <a href="/docs" style="color: #7e22ce; font-size: 0.85rem; text-decoration: none;">View Swagger API Docs (/docs)</a>
                </div>
            </body>
        </html>
        """
    )

@app.get("/lavender_bg.png")
async def serve_bg():
    bg_file = os.path.join(FRONTEND_DIST, "lavender_bg.png")
    if os.path.exists(bg_file):
        return FileResponse(bg_file)
    public_bg = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/public/lavender_bg.png"))
    if os.path.exists(public_bg):
        return FileResponse(public_bg)
    return JSONResponse(status_code=404, content={"detail": "Background image not found"})

@app.get("/pluto_logo.png")
@app.get("/nova_logo.png")
async def serve_logo():
    for name in ["pluto_logo.png", "nova_logo.png"]:
        logo_file = os.path.join(FRONTEND_DIST, name)
        if os.path.exists(logo_file):
            return FileResponse(logo_file)
        public_logo = os.path.abspath(os.path.join(os.path.dirname(__file__), f"../../frontend/public/{name}"))
        if os.path.exists(public_logo):
            return FileResponse(public_logo)
    return JSONResponse(status_code=404, content={"detail": "Logo not found"})

@app.get("/favicon.png")
async def serve_favicon():
    fav_file = os.path.join(FRONTEND_DIST, "favicon.png")
    if os.path.exists(fav_file):
        return FileResponse(fav_file)
    public_fav = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/public/favicon.png"))
    if os.path.exists(public_fav):
        return FileResponse(public_fav)
    return JSONResponse(status_code=404, content={"detail": "Favicon not found"})

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again."}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
