import { state } from "../variables";
import { fetch } from "../../../tska/polyfill/Fetch";
import Settings from "../../Settings";

// Suppress repeated error logs after this many consecutive failures.
const MAX_RETRY_LOG = 3;
let consecutiveFailures = 0;

/**
 * Normalise a companion response into the same shape that getSong() writes to
 * state.currentSongInfo, so the existing overlay and progress logic work unchanged.
 *
 * Accepts two formats:
 *  1. Generic companion format (as documented in the README / problem statement):
 *       { title, artist, album, durationMs, positionMs, isPlaying, artUrl, source }
 *  2. YouTube Music Desktop App (ytmdesktop) native format:
 *       { player: { hasSong, isPaused, seekbarCurrentPosition }, track: { title, author, album, cover, duration } }
 */
function normalizeResponse(data) {
    // --- ytmdesktop native format ---
    if (data && data.track && data.player) {
        const { track, player } = data;

        // Duration is a "m:ss" string in ytmdesktop; convert to ms.
        let durationMs = 0;
        if (track.duration) {
            const parts = String(track.duration).split(":").map(Number);
            if (parts.length === 2) durationMs = (parts[0] * 60 + parts[1]) * 1000;
        }

        return {
            name: track.title || "Unknown",
            artists: track.author ? [track.author] : ["Unknown Artist"],
            album: track.album || "",
            duration_ms: durationMs,
            progress_ms: typeof player.seekbarCurrentPosition === "number"
                ? Math.round(player.seekbarCurrentPosition * 1000)
                : 0,
            is_playing: player.hasSong === true && player.isPaused === false,
            currently_playing_type: "track",
            volume_percent: typeof player.volumePercent === "number" ? player.volumePercent : 0,
            song_image: track.cover || "https://picsum.photos/200",
            source: "YouTube Music"
        };
    }

    // --- Generic companion format ---
    if (data && ("title" in data || "isPlaying" in data)) {
        return {
            name: data.title || "Unknown",
            artists: data.artist ? [data.artist] : ["Unknown Artist"],
            album: data.album || "",
            duration_ms: typeof data.durationMs === "number" ? data.durationMs : 0,
            progress_ms: typeof data.positionMs === "number" ? data.positionMs : 0,
            is_playing: data.isPlaying === true,
            currently_playing_type: "track",
            volume_percent: 0,
            song_image: data.artUrl || "https://picsum.photos/200",
            source: data.source || "YouTube Music"
        };
    }

    return null;
}

export function getYTMSong() {
    if (!Settings.ytmEnabled) return;

    fetch(Settings.ytmEndpoint, {
        method: "GET",
        headers: { "Content-Type": "application/json" }
    })
        .then(response => {
            consecutiveFailures = 0;

            let data;
            try {
                data = JSON.parse(response);
            } catch (e) {
                console.warn("SpotPlaying YTM: Could not parse companion response.");
                return;
            }

            const info = normalizeResponse(data);
            if (!info) {
                console.warn("SpotPlaying YTM: Unrecognised response format from companion.");
                return;
            }

            state.ytmInfo = info;

            if (info.is_playing) {
                state.currentSongInfo = info;
                state.stopBarUpdating = false;
                // Sync the client-side progress timer with the reported position.
                const now = Date.now();
                state.localProgress = info.progress_ms;
                state.lastUpdateTime = now;
            } else if (
                state.currentSongInfo &&
                state.currentSongInfo.source === "YouTube Music"
            ) {
                // YTM is no longer playing; clear so Spotify can take over on its
                // next poll cycle without stale YTM data lingering.
                state.currentSongInfo = null;
                state.ytmInfo = null;
            }
        })
        .catch(error => {
            consecutiveFailures++;
            if (consecutiveFailures <= MAX_RETRY_LOG) {
                console.warn(
                    `SpotPlaying YTM: Companion unreachable at ${Settings.ytmEndpoint} – ${error}`
                );
            }
        });
}
