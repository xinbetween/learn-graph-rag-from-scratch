"""Local preview server for site/ that disables browser caching, so edits always show up on reload.
Usage: python3 tools/serve.py [port]"""
import functools, http.server, sys
from pathlib import Path

class NoCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
handler = functools.partial(NoCache, directory=str(Path(__file__).resolve().parent.parent / "site"))
print(f"Serving site/ at http://localhost:{port}/ (no-store)")
http.server.ThreadingHTTPServer(("", port), handler).serve_forever()
