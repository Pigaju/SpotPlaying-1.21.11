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
- **Media Companion integration** — display the track playing on your Mac (or any app using YouTube Music Desktop App) as an in-game overlay via a lightweight local server.

Everything in this module is customizable! From any text that is rendered on your screen, to colors, to opacity, it can be changed.

## Minecraft version

> [!NOTE]
> This module targets **Minecraft 1.21.11** with [ChatTriggers](https://chattriggers.com/#download).  
> It is **not** a compiled Fabric/Forge mod — install ChatTriggers as a regular Fabric mod, then drop the SpotPlaying folder into your `modules/` directory.

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

## Media Companion Integration

SpotPlaying can display the track you are listening to on **any app** as the same in-game overlay used for Spotify — without modifying Minecraft or installing a browser extension.

> [!NOTE]
> Minecraft **1.21.11** with [ChatTriggers](https://chattriggers.com/#download) is required.  
> The media companion works alongside the existing Spotify integration: whichever source is actively playing takes priority.

---

### Option A – macOS System Media Companion (recommended for Mac users)

This option reads the system-wide "Now Playing" information directly from macOS — the same source used by the menu-bar media controls and Control Center.  Works with **any app** that registers with macOS media sessions: Spotify, Safari, Chrome, Firefox, Music.app, Apple Podcasts, TIDAL, and more.

#### 1. Install nowplaying-cli

```bash
brew install nowplaying-cli
```

> `nowplaying-cli` reads from macOS's private `MediaRemote.framework` — the same API used by the Control Center widget. No special permissions are needed.

#### 2. Run the macOS companion server

```bash
# From the SpotPlaying directory:
python3 companion/macos-companion.py
```

You should see:

```
[SpotPlaying Companion] Listening on http://127.0.0.1:26538
  Detection mode : nowplaying-cli (system-wide)
  GET  /query    – mod polls here (every 2.0s auto-refresh)
  POST /update   – manual override for testing
Press Ctrl+C to stop.
```

Keep this terminal window open while you play Minecraft.

#### 3. Configure the mod

In Minecraft, open `/spot` settings and navigate to the **Media Companion** tab:

- Enable **"Enable Media Companion"**.
- Leave **"Companion Endpoint"** at the default: `http://localhost:26538/query`.
- Optionally adjust **"Poll Interval (ms)"** (default `2000`).

#### 4. Play something

Play any audio or video on your Mac — the in-game overlay will show the track automatically.

> **Without `nowplaying-cli`:** Pass `--no-cli` to fall back to AppleScript queries for Spotify and Music.app only.  Other apps won't be detected.
>
> ```bash
> python3 companion/macos-companion.py --no-cli
> ```

---

### Option B – YouTube Music Desktop App (zero extra code)

1. Download and install the free, open-source **[YouTube Music Desktop App](https://ytmdesktop.app/)**.
2. Open the app, go to **Settings → Integrations** and enable the **Companion Server** (it runs on `http://localhost:26538`).
3. In Minecraft, open `/spot` settings → **Media Companion** tab:
   - Enable **"Enable Media Companion"**.
   - Leave **"Companion Endpoint"** at the default: `http://localhost:26538/query`.
4. Play a song in the YouTube Music Desktop App — the overlay appears automatically.

> The mod auto-detects the YouTube Music Desktop App response format; no extra configuration is needed.

---

### Option C – Custom companion / browser bridge

If you want to push track updates from any other source (a browser extension, a custom script, another desktop app), run the generic bridge companion:

```bash
python3 companion/ytm-companion.py
```

Then `POST` track updates to `http://localhost:26538/update`:

```json
{
    "title":      "Song Title",
    "artist":     "Artist Name",
    "album":      "Album Name",
    "durationMs": 210000,
    "positionMs": 45000,
    "isPlaying":  true,
    "artUrl":     "https://example.com/cover.jpg",
    "source":     "YouTube Music"
}
```

All fields except `isPlaying` are optional.

**Quick test with curl:**

```bash
curl -s -X POST http://localhost:26538/update \
     -H "Content-Type: application/json" \
     -d '{"title":"Test Song","artist":"Test Artist","durationMs":180000,"positionMs":30000,"isPlaying":true}'
```

---

### Media Companion settings reference

| Setting | Default | Description |
|---|---|---|
| Enable Media Companion | Off | Master toggle for the companion integration |
| Companion Endpoint | `http://localhost:26538/query` | URL polled for track metadata |
| Poll Interval (ms) | `2000` | How often the mod asks for an update |

---

### Troubleshooting

**No overlay appears even though music is playing**

- Make sure the companion server is running in a terminal (`python3 companion/macos-companion.py`).
- Check that **"Enable Media Companion"** is on in `/spot` settings.
- Verify the endpoint is `http://localhost:26538/query`.
- Open the URL in a browser — you should see a JSON object. If `"isPlaying": false`, the companion isn't detecting the track yet.

**`nowplaying-cli` returns `null` for everything**

- Confirm something is actually playing: check the macOS menu-bar media controls.
- Some apps don't register with the macOS media session until audio actually starts.
- Try `nowplaying-cli get title` directly in Terminal to debug.

**Permissions dialog appears when running the companion**

- macOS may ask for Automation permission the first time the companion script queries Spotify or Music.app via AppleScript — click **Allow**.
- `nowplaying-cli` does not require any special permissions.

**Port 26538 is already in use**

- The YouTube Music Desktop App occupies port 26538 when its Companion Server is enabled.  Disable the Companion Server in the YouTube Music Desktop App, or change the port in both the companion script (`PORT = 26538`) and the mod settings.

**Overlay shows stale data after pausing**

- The companion clears the overlay within one poll interval (default 2 s) after playback stops.  Reduce **"Poll Interval (ms)"** in settings if you want faster clearing.

---

# Preview Screenshots
![Screenshot showcasing the overlay SpotPlaying provides in game, playing the song Lost Umbrella by 稲葉曇.](https://i.imgur.com/CoOl6J3.png)
![Screenshot showcasing the overlay SpotPlaying provides in game, showcasing the player controls with the song The Vampire by DECO*27](https://i.imgur.com/Hbo6vru.png)