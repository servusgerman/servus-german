# Servus German autopilot

Publishes Servus German's posts on TikTok, Instagram and YouTube without anyone uploading by hand,
and shows everything on one page: **Mission Control** (`index.html`, served by GitHub Pages).

## How it works

1. `schedule.json` lists every post of the current batch (day number, caption, media files, platforms).
2. `media/` holds the videos and slides. GitHub Pages makes them publicly reachable, which Buffer needs.
3. Twice a day, the GitHub Action in `.github/workflows/autopilot.yml` runs `autopilot.py`:
   - keeps the next 7 days scheduled in Buffer (free plan: max 10 queued posts per channel),
   - refreshes the status of every scheduled post (scheduled → posted / failed) and its engagement,
   - writes `state/queue.json` and `state/runs.json`.
4. Buffer publishes each post at its time. Mission Control reads `state/` and shows what's next, what went out, and what needs attention.

## One-time setup

| Step | Where |
|---|---|
| Connect TikTok, Instagram and YouTube in Buffer | publish.buffer.com → Channels |
| Create a Buffer API key | publish.buffer.com/settings/api |
| Store it as repo secret `BUFFER_API_KEY` | Settings → Secrets and variables → Actions |
| Turn on GitHub Pages (branch `main`, folder `/`) | Settings → Pages |
| Set `start_date` (YYYY-MM-DD) in `config.json` | this repo |

Run it once by hand: Actions → Autopilot → Run workflow. Mission Control lives at `https://<owner>.github.io/<repo>/`.

## Changing things

- **Posting times / platforms:** `config.json` (`times`, `platforms`). Times are Europe/Vienna.
- **New batch of content:** replace `schedule.json` and add the new files to `media/` (Claude does this).
- **Pinterest:** Buffer's free plan has 3 channels. For Pinterest, run `python tools/pinterest_csv.py https://<owner>.github.io/<repo>/`
  and upload `pinterest/bulk-pins.csv` in Pinterest (Create → Bulk create Pins). It schedules every pin at once.
- **Dry run:** `DRY_RUN=1 BUFFER_API_KEY=… python autopilot.py` prints what would be scheduled.

Voices in the videos are AI-generated; posts are marked as AI-generated on every platform that supports the label (`label_ai` in `config.json`).
