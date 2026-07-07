#!/usr/bin/env python3
"""
SpotPlaying – YouTube Music Companion Server
=============================================
Minecraft version: 1.21.11  |  Loader: ChatTriggers

This script provides a minimal HTTP server on localhost that the SpotPlaying
mod polls to get "now playing" metadata from YouTube Music.

HOW IT WORKS
------------
The companion exposes a single endpoint:

    GET http://localhost:26538/query

The mod polls this endpoint at the configured interval (default 2 s) and
expects a JSON response in the **generic companion format**:

    {
        "title":      "...",
        "artist":     "...",
        "album":      "...",
        "durationMs": 210000,
        "positionMs": 45000,
        "isPlaying":  true,
        "artUrl":     "http://.../cover.jpg",
        "source":     "YouTube Music"
    }

All fields except "isPlaying" are optional; the mod falls back gracefully when
they are absent.

OPTION A – YouTube Music Desktop App (recommended, zero extra code)
--------------------------------------------------------------------
Install the free, open-source YouTube Music Desktop App:
    https://ytmdesktop.app/

Enable "Companion Server" in its settings (Settings → Integrations).
The app already serves data at http://localhost:26538/query in a compatible
format – the mod detects it automatically.  You do NOT need this script.

OPTION B – Run this script as a bridge
---------------------------------------
If you use YouTube Music in a browser instead of the desktop app, you need a
way to extract the current track.  This script acts as a bridge:

  1. Install the "YouTube Music Companion" browser extension (or any extension
     that POSTs the current track to a local URL — see EXTENSION CONTRACT below).
  2. Run this script:

        python3 ytm-companion.py

  3. In SpotPlaying settings (/spot), set "Companion Endpoint" to:

        http://localhost:26538/query

  4. Enable "Enable YouTube Music" in the same settings screen.

EXTENSION CONTRACT
------------------
The browser extension should POST to http://localhost:26538/update
whenever the track changes or playback state changes:

    POST /update
    Content-Type: application/json

    {
        "title":      "Stellar",
        "artist":     "Ken Ashcorp",
        "album":      "My Kind of People",
        "durationMs": 198000,
        "positionMs": 32000,
        "isPlaying":  true,
        "artUrl":     "https://i.ytimg.com/vi/XXXX/hqdefault.jpg",
        "source":     "YouTube Music"
    }

The script caches the last received payload and serves it via GET /query.

TESTING WITHOUT A BROWSER EXTENSION
-------------------------------------
Run the script and POST a test payload manually:

    curl -s -X POST http://localhost:26538/update \\
         -H "Content-Type: application/json" \\
         -d '{"title":"Test Song","artist":"Test Artist","durationMs":180000,"positionMs":30000,"isPlaying":true}'

Then check that the mod overlay appears in-game.

DEPENDENCIES
------------
Python ≥ 3.8, no third-party packages required (uses stdlib http.server).
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "127.0.0.1"
PORT = 26538

# ── Shared state (protected by a lock) ───────────────────────────────────────

_lock = threading.Lock()
_current_track: dict = {
    "title": "",
    "artist": "",
    "album": "",
    "durationMs": 0,
    "positionMs": 0,
    "isPlaying": False,
    "artUrl": "",
    "source": "YouTube Music",
}
# We track when positionMs was last reported so we can estimate the live
# position between updates (avoids needing a very fast poll rate).
_position_updated_at: float = time.time()


def _get_live_position() -> int:
    """Return estimated current position in ms, extrapolating from last update."""
    with _lock:
        if not _current_track["isPlaying"]:
            return _current_track["positionMs"]
        elapsed_ms = int((time.time() - _position_updated_at) * 1000)
        duration = _current_track["durationMs"]
        pos = _current_track["positionMs"] + elapsed_ms
        return min(pos, duration) if duration > 0 else pos


def _build_response() -> dict:
    with _lock:
        data = dict(_current_track)
    data["positionMs"] = _get_live_position()
    return data


# ── HTTP handler ─────────────────────────────────────────────────────────────

class CompanionHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):  # silence default access log
        pass

    # ------------------------------------------------------------------
    # GET /query  – the mod polls this
    # ------------------------------------------------------------------
    def do_GET(self):
        if self.path.startswith("/query"):
            payload = json.dumps(_build_response()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_response(404)
            self.end_headers()

    # ------------------------------------------------------------------
    # POST /update  – browser extension pushes updates here
    # ------------------------------------------------------------------
    def do_POST(self):
        global _position_updated_at

        if self.path.startswith("/update"):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                incoming = json.loads(body)
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                return

            with _lock:
                _current_track["title"] = str(incoming.get("title", ""))
                _current_track["artist"] = str(incoming.get("artist", ""))
                _current_track["album"] = str(incoming.get("album", ""))
                _current_track["durationMs"] = int(incoming.get("durationMs", 0))
                _current_track["positionMs"] = int(incoming.get("positionMs", 0))
                _current_track["isPlaying"] = bool(incoming.get("isPlaying", False))
                _current_track["artUrl"] = str(incoming.get("artUrl", ""))
                _current_track["source"] = str(incoming.get("source", "YouTube Music"))
                _position_updated_at = time.time()

            self.send_response(204)
            self.end_headers()
            print(
                f"[SpotPlaying Companion] Now playing: "
                f"{_current_track['title']} – {_current_track['artist']} "
                f"({'playing' if _current_track['isPlaying'] else 'paused'})"
            )
        else:
            self.send_response(404)
            self.end_headers()

    # OPTIONS for CORS pre-flight (browser extensions need this)
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    server = HTTPServer((HOST, PORT), CompanionHandler)
    print(f"[SpotPlaying Companion] Listening on http://{HOST}:{PORT}")
    print(f"  GET  /query  – mod polls here")
    print(f"  POST /update – browser extension posts here")
    print(f"Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[SpotPlaying Companion] Stopped.")


if __name__ == "__main__":
    main()
