# ticket-notifier

Monitors ticket sale pages and alerts you (sound + macOS notification) the moment availability changes. Uses a real browser (Playwright/Chromium) so JavaScript-rendered content is handled correctly.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Usage

**Option 1 — `urls.txt`** (default)

Edit `urls.txt`, one URL per line, then run:

```bash
python monitor.py
```

**Option 2 — CLI args**

```bash
python monitor.py https://example.com/event1 https://example.com/event2
```

CLI args take priority over `urls.txt`.

## Configuration

Edit `config.yaml`:

| Key | Default | Description |
|---|---|---|
| `not_available_text` | `"Currently, no tickets are on sale..."` | Text whose *absence* signals availability |
| `interval_seconds` | `10` | Seconds between check rounds |
| `jitter_seconds` | `4` | Random extra delay added per round (avoids bot-like patterns) |
| `headless` | `true` | Set to `false` to watch the browser |
| `alarm_beeps` | `5` | Number of beeps when tickets are found |

## How it works

1. All URLs are checked in parallel each round.
2. If the `not_available_text` string is no longer present on the page, a ticket is considered available.
3. On detection: plays `Glass.aiff` N times and sends a macOS notification banner.
4. Cookie/consent banners are dismissed automatically (once per session per URL).
