import sys
import os
import traceback

# Ensure backend root is in sys.path
current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from app.main import app
except Exception as exc:
    err_tb = traceback.format_exc()
    print("FATAL: Failed to import app.main in backend/main.py:\n", err_tb, file=sys.stderr)

    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI(title="Pluto AI Startup Diagnostic")

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
    def diagnostic_fallback(full_path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Backend Startup Failure",
                "detail": str(exc),
                "traceback": err_tb,
                "python_version": sys.version,
                "cwd": os.getcwd(),
                "sys_path": sys.path,
                "files_in_dir": os.listdir(current_dir) if os.path.isdir(current_dir) else [],
            }
        )

__all__ = ["app"]
