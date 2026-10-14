import sys
import os
import traceback
import json

# Add candidate backend directories to sys.path
current_dir = os.path.abspath(os.path.dirname(__file__))
candidates = [
    os.path.abspath(os.path.join(current_dir, "..", "backend")),
    os.path.abspath(os.path.join(current_dir, "backend")),
    os.path.abspath(os.path.join(os.getcwd(), "backend")),
    "/var/task/backend",
]

for c in candidates:
    if os.path.isdir(c) and c not in sys.path:
        sys.path.insert(0, c)

try:
    from app.main import app
except Exception as exc:
    err_tb = traceback.format_exc()
    print("FATAL: Failed to import app.main:\n", err_tb, file=sys.stderr)

    async def app(scope, receive, send):
        if scope["type"] == "http":
            body = json.dumps({
                "error": "Serverless Startup Failure",
                "detail": str(exc),
                "traceback": err_tb,
                "sys_path": sys.path,
                "cwd": os.getcwd(),
                "candidates_checked": [f"{c} (exists={os.path.isdir(c)})" for c in candidates],
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
