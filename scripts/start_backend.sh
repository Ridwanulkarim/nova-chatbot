#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

echo "Starting Nova AI Backend on http://127.0.0.1:8000 ..."
export PYTHONPATH="$DIR/backend/.venv/lib/python3.9/site-packages:$DIR/backend:$PYTHONPATH"
/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
