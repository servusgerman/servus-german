#!/usr/bin/env python3
"""Write pinterest/bulk-pins.csv for Pinterest's "Bulk create Pins" upload (desktop: Create → Bulk create Pins).
Includes the 10 infographic pins plus every video as a video Pin, each with a publish date.
Usage: python tools/pinterest_csv.py https://<owner>.github.io/<repo>/  [board name]"""
import csv, json, sys, datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
base = sys.argv[1].rstrip("/") + "/"
board = sys.argv[2] if len(sys.argv) > 2 else "Learn German"
cfg = json.load(open(ROOT / "config.json"))
sched = json.load(open(ROOT / "schedule.json"))
tz = ZoneInfo(cfg["timezone"])
start = dt.date.fromisoformat(cfg["start_date"])
link = (cfg.get("links") or {}).get("shop") or ""
rows = []
for p in sched["posts"]:
    if p["kind"] not in ("pin", "video"):
        continue
    day = start + dt.timedelta(days=p["day"] - 1)
    hh, mm = (20, 0) if p["kind"] == "pin" else (21, 0)
    when = dt.datetime(day.year, day.month, day.day, hh, mm, tzinfo=tz).astimezone(dt.timezone.utc)
    desc = p["caption"] if p["kind"] == "pin" else p["caption"].split(" #")[0]
    rows.append({"Title": p["title"][:100], "Media URL": base + p["media"][0], "Pinterest board": board,
                 "Thumbnail": (base + p["cover"]) if p["kind"] == "video" else "", "Description": desc[:500],
                 "Link": link, "Publish date": when.strftime("%Y-%m-%dT%H:%M:%S"),
                 "Keywords": "learn german, german vocabulary, austrian german, vienna"})
out = ROOT / "pinterest/bulk-pins.csv"
out.parent.mkdir(exist_ok=True)
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print(f"{len(rows)} pins → {out}")
