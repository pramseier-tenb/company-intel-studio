#!/bin/bash
# Double-click launcher for macOS. Starts the local Intel Studio web app.
cd "$(dirname "$0")" || exit 1
python3 -c "import reportlab" 2>/dev/null || {
  echo "Installing reportlab (one-time, for PDF export)..."
  python3 -m pip install --user reportlab
}
exec python3 app.py
