"""
Vercel serverless entrypoint: forwards all /api/* requests to the Flask app.
Vercel expects functions in the api/ directory; this ensures the Flask app
is invoked with the correct request method (POST, etc.) and path.
"""
import sys
from pathlib import Path

# Ensure backend is on the path when running from project root (Vercel)
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from backend.app import app
