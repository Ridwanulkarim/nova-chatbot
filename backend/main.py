import sys
import os
import traceback
import json

# Ensure backend root is in sys.path
current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from app.main import app
except Exception as exc:
    err_tb = traceback.format_exc()
    print("FATAL: Failed to import app.main in backend/main.py:\n", err_tb, file=sys.stderr)

    async def app(scope, receive, send):
        if scope["type"] == "http":
            body = json.dumps({
                "error": "Backend Service Startup Failure",
                "detail": str(exc),
                "traceback": err_tb,
                "sys_path": sys.path,
                "cwd": os.getcwd(),
                "files_in_dir": os.listdir(current_dir) if os.path.isdir(current_dir) else [],
            }, indent=2).encode("utf-8")
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"content-length", str(len(body)).encode("utf-8")],
                    [b"access-control-allow-origin", b"*"],
                ],
            })
            await send({
                "type": "http.response.body",
                "body": body,
            })

__all__ = ["app"]
