#!/usr/bin/env python3
"""
SpotPlaying – macOS System Media Companion
==========================================
Minecraft version: 1.21.11  |  Loader: ChatTriggers

Reads the system-wide "Now Playing" information from macOS and serves it on
localhost so the SpotPlaying overlay can display it in-game.

Works with ANY app that registers with the macOS media session system:
  Spotify, Safari, Chrome, Firefox, Music.app, Apple Podcasts, TIDAL, etc.

HOW IT WORKS
------------
The companion polls macOS for the current "Now Playing" track every 2 seconds
and caches it.  The SpotPlaying mod polls:

    GET http://localhost:26538/query

and expects a JSON response:

    {
        "title":      "...",
        "artist":     "...",
        "album":      "...",
        "durationMs": 210000,
        "positionMs": 45000,
        "isPlaying":  true,
        "artUrl":     "",
        "source":     "Spotify"
    }

All fields except "isPlaying" are optional; the mod falls back gracefully.

QUICK START
-----------
1. Install nowplaying-cli (reads from the same macOS API as Control Center):

       brew install nowplaying-cli

2. Run this script:

       python3 companion/macos-companion.py

3. In Minecraft open /spot settings → "Media Companion" tab:
   - Enable "Enable Media Companion"
   - Set "Companion Endpoint" to http://localhost:26538/query
   - Leave "Poll Interval (ms)" at 2000

4. Play any media on your Mac — the overlay appears automatically.

WITHOUT nowplaying-cli (limited app support)
---------------------------------------------
If you cannot install nowplaying-cli, the script falls back to AppleScript
queries for Spotify and Music.app.  Other apps won't be detected.

To try the fallback-only mode, pass --no-cli:

       python3 companion/macos-companion.py --no-cli

PERMISSIONS
-----------
No special permissions are required for nowplaying-cli or AppleScript
(Spotify / Music.app).  macOS may show a permissions dialog the first time
a script automates an app via AppleScript — click "Allow" if prompted.

MANUAL TESTING
--------------
Push a test payload directly to check the endpoint without any media playing:

    curl -s -X POST http://localhost:26538/update \\
         -H "Content-Type: application/json" \\
         -d '{"title":"Test","artist":"Artist","durationMs":180000,"positionMs":30000,"isPlaying":true}'

Then check http://localhost:26538/query or look for the in-game overlay.

DEPENDENCIES
------------
Python ≥ 3.8, no third-party packages required (uses stdlib only).
Optional: nowplaying-cli ≥ 1.0  (brew install nowplaying-cli)
"""

import json
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, Optional

HOST = "127.0.0.1"
PORT = 26538
POLL_INTERVAL = 2.0  # seconds between system media polls

# ── Bundle-identifier → friendly source name ──────────────────────────────────

_BUNDLE_NAMES: Dict[str, str] = {
    "com.spotify.client":        "Spotify",
    "com.apple.Music":           "Music",
    "com.apple.iTunes":          "iTunes",
    "com.google.Chrome":         "Chrome",
    "com.apple.Safari":          "Safari",
    "org.mozilla.firefox":       "Firefox",
    "com.microsoft.edgemac":     "Edge",
    "com.apple.podcasts":        "Podcasts",
    "com.tidal.desktop":         "TIDAL",
    "com.deezer.Deezer":         "Deezer",
    "com.plexapp.plex":          "Plex",
    "tv.plex.plexamp":           "Plexamp",
    "co.mochiapp.Mochi":         "Mochi",
    "com.apple.TV":              "Apple TV",
}

# Fields requested from nowplaying-cli in this exact order
_CLI_FIELDS = [
    "title", "artist", "album",
    "duration", "elapsedTime", "playbackRate",
    "bundleIdentifier",
]

# ── Shared state (protected by a lock) ────────────────────────────────────────

_lock = threading.Lock()
_current_track: dict = {
    "title": "",
    "artist": "",
    "album": "",
    "durationMs": 0,
    "positionMs": 0,
    "isPlaying": False,
    "artUrl": "",
    "source": "",
}
_position_updated_at: float = time.time()


def _set_track(data: dict) -> None:
    """Thread-safe update of the cached track info."""
    global _position_updated_at
    with _lock:
        _current_track.update(data)
        _position_updated_at = time.time()


def _get_live_position() -> int:
    """Estimated current position in ms, extrapolating since last update."""
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


# ── Media detection back-ends ─────────────────────────────────────────────────

def _query_nowplaying_cli() -> Optional[dict]:
    """
    Read now-playing info via nowplaying-cli (brew install nowplaying-cli).
    Returns a track dict, or None if nowplaying-cli is unavailable / nothing playing.
    """
    try:
        result = subprocess.run(
            ["nowplaying-cli", "get"] + _CLI_FIELDS,
            capture_output=True, text=True, timeout=5,
        )
    except FileNotFoundError:
        return None  # nowplaying-cli not installed
    except subprocess.TimeoutExpired:
        return None

    if result.returncode != 0:
        return None

    lines = result.stdout.splitlines()
    if len(lines) < len(_CLI_FIELDS):
        return None

    values = dict(zip(_CLI_FIELDS, lines))

    def _val(key: str, default: str = "") -> str:
        v = values.get(key, "null").strip()
        return default if v == "null" else v

    title = _val("title")
    # Nothing playing when title is absent
    if not title:
        return {
            "title": "", "artist": "", "album": "",
            "durationMs": 0, "positionMs": 0,
            "isPlaying": False, "artUrl": "", "source": "",
        }

    try:
        duration_ms = int(float(_val("duration", "0")) * 1000)
    except ValueError:
        duration_ms = 0

    try:
        position_ms = int(float(_val("elapsedTime", "0")) * 1000)
    except ValueError:
        position_ms = 0

    try:
        rate = float(_val("playbackRate", "0"))
    except ValueError:
        rate = 0.0

    bundle = _val("bundleIdentifier")
    source = _BUNDLE_NAMES.get(bundle, bundle.rsplit(".", 1)[-1] if bundle else "Unknown")

    return {
        "title": title,
        "artist": _val("artist"),
        "album": _val("album"),
        "durationMs": duration_ms,
        "positionMs": position_ms,
        "isPlaying": rate > 0.0,
        "artUrl": "",
        "source": source,
    }


def _run_applescript(script: str) -> Optional[str]:
    """
    Run an AppleScript snippet via osascript and return its stdout output.

    :param script: A single-line or multi-line AppleScript expression to evaluate.
    :returns: The stripped stdout string on success, or None if the script fails
              or times out.
    """
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def _query_applescript_spotify() -> Optional[dict]:
    """
    Fallback: read now-playing info from the Spotify desktop app via AppleScript.
    Returns None if Spotify is not running or not playing.
    """
    state_raw = _run_applescript('tell application "Spotify" to get player state')
    if state_raw != "playing":
        return None

    fields = {
        "name":     _run_applescript('tell application "Spotify" to get name of current track'),
        "artist":   _run_applescript('tell application "Spotify" to get artist of current track'),
        "album":    _run_applescript('tell application "Spotify" to get album of current track'),
        "duration": _run_applescript('tell application "Spotify" to get duration of current track'),
        "position": _run_applescript('tell application "Spotify" to get player position'),
    }

    try:
        # Spotify AppleScript returns duration in ms, position in seconds
        dur_ms = int(fields["duration"] or 0)
    except ValueError:
        dur_ms = 0
    try:
        pos_ms = int(float(fields["position"] or 0) * 1000)
    except ValueError:
        pos_ms = 0

    return {
        "title":      fields["name"] or "",
        "artist":     fields["artist"] or "",
        "album":      fields["album"] or "",
        "durationMs": dur_ms,
        "positionMs": pos_ms,
        "isPlaying":  True,
        "artUrl":     "",
        "source":     "Spotify",
    }


def _query_applescript_music() -> Optional[dict]:
    """
    Fallback: read now-playing info from Music.app via AppleScript.
    Returns None if Music.app is not running or not playing.
    """
    state_raw = _run_applescript('tell application "Music" to get player state')
    if state_raw != "playing":
        return None

    fields = {
        "name":     _run_applescript('tell application "Music" to get name of current track'),
        "artist":   _run_applescript('tell application "Music" to get artist of current track'),
        "album":    _run_applescript('tell application "Music" to get album of current track'),
        "duration": _run_applescript('tell application "Music" to get duration of current track'),
        "position": _run_applescript('tell application "Music" to get player position'),
    }

    try:
        dur_ms = int(float(fields["duration"] or 0) * 1000)
    except ValueError:
        dur_ms = 0
    try:
        pos_ms = int(float(fields["position"] or 0) * 1000)
    except ValueError:
        pos_ms = 0

    return {
        "title":      fields["name"] or "",
        "artist":     fields["artist"] or "",
        "album":      fields["album"] or "",
        "durationMs": dur_ms,
        "positionMs": pos_ms,
        "isPlaying":  True,
        "artUrl":     "",
        "source":     "Music",
    }


# ── Background poll loop ───────────────────────────────────────────────────────

def _poll_loop(use_cli: bool) -> None:
    """Continuously poll macOS for now-playing info and update cached state."""
    while True:
        track = None

        if use_cli:
            track = _query_nowplaying_cli()

        if track is None:
            # CLI unavailable or returned None — try AppleScript fallbacks
            track = _query_applescript_spotify() or _query_applescript_music()

        if track is None:
            # Nothing detected; mark as not playing but preserve last metadata
            with _lock:
                _current_track["isPlaying"] = False
        else:
            _set_track(track)

        time.sleep(POLL_INTERVAL)


# ── HTTP handler ───────────────────────────────────────────────────────────────

class CompanionHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):  # noqa: D102
        """Suppress the default per-request access log printed to stderr."""
        pass

    # GET /query  – the mod polls this
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

    # POST /update  – manual override / testing
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
                _current_track["title"]      = str(incoming.get("title", ""))
                _current_track["artist"]     = str(incoming.get("artist", ""))
                _current_track["album"]      = str(incoming.get("album", ""))
                _current_track["durationMs"] = int(incoming.get("durationMs", 0))
                _current_track["positionMs"] = int(incoming.get("positionMs", 0))
                _current_track["isPlaying"]  = bool(incoming.get("isPlaying", False))
                _current_track["artUrl"]     = str(incoming.get("artUrl", ""))
                _current_track["source"]     = str(incoming.get("source", "Manual"))
                _position_updated_at = time.time()

            self.send_response(204)
            self.end_headers()
            print(
                f"[SpotPlaying Companion] Manual override: "
                f"{_current_track['title']} – {_current_track['artist']} "
                f"({'playing' if _current_track['isPlaying'] else 'paused'})"
            )
        else:
            self.send_response(404)
            self.end_headers()

    # OPTIONS for CORS pre-flight
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    use_cli = "--no-cli" not in sys.argv

    if use_cli:
        # Check that nowplaying-cli is available
        probe = subprocess.run(
            ["nowplaying-cli", "--version"],
            capture_output=True, timeout=5,
        )
        if probe.returncode != 0:
            print(
                "[SpotPlaying Companion] WARNING: nowplaying-cli not found.\n"
                "  Install it with:  brew install nowplaying-cli\n"
                "  Falling back to AppleScript (Spotify and Music.app only).\n"
                "  To suppress this warning run with --no-cli.\n"
            )
            use_cli = False

    # Start the background polling thread (daemon so it exits with main process)
    poll_thread = threading.Thread(target=_poll_loop, args=(use_cli,), daemon=True)
    poll_thread.start()

    server = HTTPServer((HOST, PORT), CompanionHandler)
    mode = "nowplaying-cli (system-wide)" if use_cli else "AppleScript (Spotify / Music.app)"
    print(f"[SpotPlaying Companion] Listening on http://{HOST}:{PORT}")
    print(f"  Detection mode : {mode}")
    print(f"  GET  /query    – mod polls here (every {POLL_INTERVAL}s auto-refresh)")
    print(f"  POST /update   – manual override for testing")
    print(f"Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[SpotPlaying Companion] Stopped.")


if __name__ == "__main__":
    main()
