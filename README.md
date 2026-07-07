> [!NOTE]
> This module requires [ChatTriggers](https://chattriggers.com/#download) to use.

# SpotPlaying
The _all-in-one_ Spotify Integration for Minecraft.

## Features
- Displays your currently playing **Song** and **Artist**.
- Shows the song cover image of the playing song.
- A progress bar that shows your length into a song.
- Player Controls, including Pausing/Skipping, Rewinding/Fastforwarding, and Volume Controls.
- Search for playlists and play them directly in-game.
- Show the lyrics of a song while it is playing.
- Keybinds to control everything from your keyboard.
- **YouTube Music integration** via a local companion app or [YouTube Music Desktop App](https://ytmdesktop.app/).

Everything in this module is customizable! From any text that is rendered on your screen, to colors, to opacity, it can be changed.

## Installation

### Method 1
> 1. Navigate to the [releases tab](https://github.com/tdarth/SpotPlaying/releases/latest) and install ```SpotPlaying.zip```.
> 
> 2. Extract this file to your modules folder, which can be found in ```/ct files -> modules```.
>
> 3. Finally, type ```/ct load```

### Method 2 (not recommended)
> 1. Type ```/ct import SpotPlaying``` in the Minecraft Chat.
> - The module isn't frequently updated here.

After installing the module, type ```/spot tutorial``` in-game to setup the module.

---

## YouTube Music Integration

SpotPlaying can display the track you are listening to on **YouTube Music** as the same in-game overlay used for Spotify.

> [!NOTE]
> Minecraft version **1.21.11** with [ChatTriggers](https://chattriggers.com/#download) is required.  
> YouTube Music integration works alongside the existing Spotify integration: whichever source is actively playing takes priority.

### Option A – YouTube Music Desktop App (recommended, no extra setup)

1. Download and install the free, open-source **[YouTube Music Desktop App](https://ytmdesktop.app/)**.
2. Open the app, go to **Settings → Integrations** and enable the **Companion Server** (it runs on `http://localhost:26538`).
3. In Minecraft, open `/spot` settings, navigate to the **YouTube Music** tab, and:
   - Enable **"Enable YouTube Music"**.
   - Leave **"Companion Endpoint"** at the default: `http://localhost:26538/query`.
4. Play a song in the YouTube Music Desktop App — the overlay appears automatically.

> The mod auto-detects the YouTube Music Desktop App response format; no extra configuration is needed.

---

### Option B – Browser + companion script

Use this option if you listen to YouTube Music in a browser (Chrome, Firefox, etc.) instead of the desktop app.

#### 1. Run the companion server

```bash
# Python 3.8+ required; no third-party packages needed
python3 companion/ytm-companion.py
```

You should see:

```
[SpotPlaying Companion] Listening on http://127.0.0.1:26538
  GET  /query  – mod polls here
  POST /update – browser extension posts here
Press Ctrl+C to stop.
```

#### 2. Push track updates to the companion

The companion server exposes a `POST /update` endpoint that accepts the track
payload. You can push updates from:

- A **browser extension** (userscript, content script, etc.) that reads the
  current YouTube Music page and POSTs to `http://localhost:26538/update`.
- Any external tool or script that knows the current track.

**Payload contract** (`POST http://localhost:26538/update`):

```json
{
    "title":      "Song Title",
    "artist":     "Artist Name",
    "album":      "Album Name",
    "durationMs": 210000,
    "positionMs": 45000,
    "isPlaying":  true,
    "artUrl":     "https://i.ytimg.com/vi/XXXX/hqdefault.jpg",
    "source":     "YouTube Music"
}
```

All fields except `isPlaying` are optional; missing values fall back gracefully
(empty strings / 0 / placeholder artwork).

**Quick test with curl:**

```bash
curl -s -X POST http://localhost:26538/update \
     -H "Content-Type: application/json" \
     -d '{"title":"Test Song","artist":"Test Artist","durationMs":180000,"positionMs":30000,"isPlaying":true}'
```

#### 3. Configure the mod

In Minecraft, open `/spot` settings, navigate to the **YouTube Music** tab, and:

- Enable **"Enable YouTube Music"**.
- Set **"Companion Endpoint"** to `http://localhost:26538/query`.
- Optionally adjust **"Poll Interval (ms)"** (default `2000`).

---

### YouTube Music settings reference

| Setting | Default | Description |
|---|---|---|
| Enable YouTube Music | Off | Master toggle for the YTM integration |
| Companion Endpoint | `http://localhost:26538/query` | URL polled for track metadata |
| Poll Interval (ms) | `2000` | How often the mod asks for an update |

---

# Preview Screenshots
![Screenshot showcasing the overlay SpotPlaying provides in game, playing the song Lost Umbrella by 稲葉曇.](https://i.imgur.com/CoOl6J3.png)
![Screenshot showcasing the overlay SpotPlaying provides in game, showcasing the player controls with the song The Vampire by DECO*27](https://i.imgur.com/Hbo6vru.png)