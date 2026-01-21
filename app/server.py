import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

INDEX_PATH = "app/ui/static/index.html"
SEED_PATH = "app/data/seed/sample-policies.md"


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def html_response(handler: BaseHTTPRequestHandler, status: int, content: str):
    data = content.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


class Handler(BaseHTTPRequestHandler):
    server_version = "HiveAssistantHTTP/0.1"

    def log_message(self, format, *args):
        # Structured log lines (JSON) with timestamp and request line
        payload = {
            "ts": self.log_date_time_string(),
            "client": self.client_address[0],
            "method": self.command,
            "path": self.path,
            "msg": format % args,
        }
        sys.stderr.write(json.dumps(payload) + "\n")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            return json_response(self, 200, {"status": "ok"})
        if parsed.path == "/demo":
            return json_response(
                self,
                200,
                {
                    "message": "Vacation policy allows 20 days per year (example).",
                    "citations": [{"doc": os.path.basename(SEED_PATH), "section": "Vacation Policy §1"}],
                },
            )
        if parsed.path == "/":
            try:
                with open(INDEX_PATH, "r", encoding="utf-8") as f:
                    return html_response(self, 200, f.read())
            except FileNotFoundError:
                return json_response(self, 500, {"error": "UI not found"})
        # Simple static fallback not required; keep endpoints minimal
        return json_response(self, 404, {"error": "Not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/ask":
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length > 0 else b"{}"
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                return json_response(self, 400, {"error": "Invalid JSON"})
            citations = payload.get("citations", [])
            if not isinstance(citations, list) or len(citations) == 0:
                return json_response(
                    self,
                    400,
                    {
                        "error": "This system requires source citations. Please provide or ingest documents and reference at least one source.",
                    },
                )
            # Minimal format validation
            for c in citations:
                if not isinstance(c, dict) or not c.get("doc") or not c.get("section"):
                    return json_response(self, 400, {"error": "Invalid citation format. Expected {doc, section}."})
            return json_response(
                self,
                200,
                {
                    "message": "Answer would be generated here.",
                    "citations": citations,
                    "note": "MVP enforces citations; retrieval/generation is future work.",
                },
            )
        return json_response(self, 404, {"error": "Not found"})


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    httpd = HTTPServer((host, port), Handler)
    print(json.dumps({"status": "starting", "host": host, "port": port}))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
