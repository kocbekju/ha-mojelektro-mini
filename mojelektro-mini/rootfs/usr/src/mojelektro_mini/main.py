from __future__ import annotations

import html
import json
import logging
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


OPTIONS_PATH = Path("/data/options.json")
HOST = "0.0.0.0"
PORT = 8099


def load_options() -> dict[str, Any]:
    if not OPTIONS_PATH.exists():
        return {}

    with OPTIONS_PATH.open("r", encoding="utf-8") as options_file:
        data = json.load(options_file)

    if not isinstance(data, dict):
        raise ValueError("/data/options.json must contain a JSON object")

    return data


def sanitized_options(options: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(options)
    if "mojelektro_password" in sanitized:
        sanitized["mojelektro_password"] = "***" if sanitized["mojelektro_password"] else ""
    return sanitized


class Handler(BaseHTTPRequestHandler):
    server_version = "MojelektroMini/0.1"

    def do_GET(self) -> None:
        if self.path in ("/", ""):
            self.respond_html(self.status_page())
            return

        if self.path == "/health":
            self.respond_json({"status": "ok", "service": "mojelektro-mini"})
            return

        if self.path == "/options":
            self.respond_json(sanitized_options(load_options()))
            return

        self.respond_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        logging.info("%s - %s", self.address_string(), format % args)

    def respond_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def respond_html(self, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def status_page(self) -> str:
        options = sanitized_options(load_options())
        username = html.escape(str(options.get("mojelektro_username", "")))
        interval = html.escape(str(options.get("poll_interval_minutes", "")))
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mojelektro Mini</title>
  <style>
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f6f8fb;
      color: #1f2933;
    }}
    main {{
      max-width: 720px;
      margin: 48px auto;
      padding: 0 20px;
    }}
    h1 {{
      font-size: 28px;
      margin: 0 0 12px;
    }}
    dl {{
      display: grid;
      grid-template-columns: 180px 1fr;
      gap: 10px 16px;
      margin-top: 24px;
    }}
    dt {{
      font-weight: 650;
    }}
    dd {{
      margin: 0;
    }}
    code {{
      background: #e8edf3;
      border-radius: 4px;
      padding: 2px 5px;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Mojelektro Mini</h1>
    <p>Add-on service is running.</p>
    <dl>
      <dt>Username</dt>
      <dd>{username or "<em>not configured</em>"}</dd>
      <dt>Poll interval</dt>
      <dd>{interval or "<em>not configured</em>"} minutes</dd>
      <dt>Health</dt>
      <dd><code>/health</code></dd>
    </dl>
  </main>
</body>
</html>
"""


def configure_logging() -> None:
    level_name = os.environ.get("LOG_LEVEL", "info").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    configure_logging()
    logging.info("Mojelektro Mini listening on %s:%s", HOST, PORT)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
