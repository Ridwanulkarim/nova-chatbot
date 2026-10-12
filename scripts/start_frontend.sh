#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR/frontend"

echo "Starting Nova AI Frontend on http://localhost:5180 ..."
npm run dev
