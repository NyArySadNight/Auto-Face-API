# Auto-Face-API

A desktop tool (tkinter) that auto-posts to a Facebook Page (Fanpage) on a
custom schedule — randomly picking one of 5 pre-written posts, each with a
random image/video attached from a folder you choose.

Uses the **official Facebook Graph API** (no fake browser login), so it
doesn't violate Facebook's terms and carries no risk of account suspension
from fake-automation behavior.

> Requires a Page ID + Page Access Token before use — use
> [Auto-Get-Face-Access-Token](../Auto-Get-Face-Access-Token) to get one
> automatically, or fetch one manually via the Graph API Explorer.

## Features

- Posts to your Fanpage on a custom interval (minutes).
- Pre-write up to **5 post contents**; each run randomly picks one (and
  avoids repeating the post used last time, if more than one is available).
- Automatically attaches 1 **random** image or video from a chosen folder
  (default `~/Downloads/VidFaceAutoFix`) — can be disabled for text-only
  posts.
- Supported image formats: `.jpg .jpeg .png .gif .bmp .webp`; video:
  `.mp4 .mov .avi .mkv .webm .m4v`.
- "Post now" button to test your setup before starting the automatic loop.
- Activity log shown right in the app (success/failure per post).

## Requirements

- Python 3.9+ (tkinter usually ships with Python; on Ubuntu/Debian if
  missing: `sudo apt install python3-tk`)
- Dependency:

```bash
pip install requests
```

## Before you start

1. **Page ID** and **Page Access Token** for the Fanpage (see
   [Auto-Get-Face-Access-Token](../Auto-Get-Face-Access-Token) to get these
   automatically, written straight into the shared config file).
2. Up to 5 sample post contents.
3. (Optional) A folder of images/videos to attach randomly.

## Running

```bash
python3 AutoFixFace.py
```

In the app: enter Page ID + Access Token (or leave blank if already saved
by Auto-Get-Face-Access-Token), fill in your post contents, pick a media
folder (if using one), click **Save config**, then **▶ Start** to begin the
automatic posting loop.

## Configuration

Stored in `fb_autopost_config.json` in the script's directory: `page_id`,
`access_token`, posting interval (minutes), the list of posts, and the
media folder.

## Security

- **Access Token** is stored as plain text in `fb_autopost_config.json` —
  **never commit this file to Git**. Add it to `.gitignore`:
  ```
  fb_autopost_config.json
  ```
- If a token ever leaks, revoke it immediately at **Facebook → Settings →
  Security → Apps and Websites**.

## Want a long-lived Page Token (won't expire after 1-2 hours)?

If you got your token manually (without using the
Auto-Get-Face-Access-Token repo), exchange a short-lived token for a
long-lived one:

```bash
curl -i -X GET "https://graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_TOKEN"
```

Then use the long-lived **user** token to call `/me/accounts` and get a
**Page** token — Page tokens obtained this way usually don't expire.

## Notes

- The original README listed the run command as `python3 fb_autopost.py` —
  the actual filename in this repo is **`AutoFixFace.py`**; this README
  corrects that.
- Posting too frequently, or with repetitive content, may get flagged as
  spam by Facebook and hurt your Page's reach — use a reasonable interval
  and vary your content.
