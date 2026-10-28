#!/usr/bin/env python3
"""Servus German autopilot.

Runs daily (GitHub Actions). Keeps the next few days of posts scheduled in Buffer
(TikTok, Instagram, YouTube) using media hosted on this repo's GitHub Pages site,
refreshes the status of everything already scheduled, and writes state/*.json for the
Mission Control dashboard (index.html).

Standard library only. Environment:
  BUFFER_API_KEY   Buffer personal API key (repo secret)       — required unless --mock
  PAGES_BASE       public base URL of the media (default: https://<owner>.github.io/<repo>/)
  DRY_RUN=1        plan only, write nothing to Buffer
"""
import json, os, sys, time, datetime as dt, urllib.request, urllib.error
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state"
STATE.mkdir(exist_ok=True)
API = os.environ.get("BUFFER_API", "https://api.buffer.com")
SERVICES = ("tiktok", "instagram", "youtube", "pinterest")


def now_utc():
    fake = os.environ.get("AUTOPILOT_NOW")          # used by the offline test suite only
    if fake:
        return dt.datetime.fromisoformat(fake.replace("Z", "+00:00"))
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def parse_iso(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def load(name, default):
    p = ROOT / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def save(name, data):
    p = ROOT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=False), encoding="utf-8")


# ---------------------------------------------------------------- GraphQL helpers
class Enum(str):
    """A GraphQL enum literal (written without quotes)."""


def lit(v):
    """Python value -> GraphQL input literal."""
    if isinstance(v, Enum):
        return str(v)
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, (int, float)):
        return json.dumps(v)
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(lit(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}: {lit(x)}" for k, x in v.items() if x is not None) + "}"
    raise TypeError(type(v))


class Buffer:
    def __init__(self, key):
        self.key = key
        self.calls = 0

    def q(self, query, retries=2):
        body = json.dumps({"query": query}).encode()
        req = urllib.request.Request(API, data=body, method="POST", headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {self.key}",
            "User-Agent": "servus-german-autopilot/1.0"})
        for attempt in range(retries + 1):
            try:
                self.calls += 1
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = json.loads(r.read().decode())
                if data.get("errors"):
                    raise RuntimeError("; ".join(e.get("message", str(e)) for e in data["errors"]))
                return data["data"]
            except urllib.error.HTTPError as e:
                msg = e.read().decode(errors="replace")[:500]
                if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                    time.sleep(5 * (attempt + 1)); continue
                raise RuntimeError(f"HTTP {e.code}: {msg}")
            except urllib.error.URLError as e:
                if attempt < retries:
                    time.sleep(5 * (attempt + 1)); continue
                raise RuntimeError(f"network: {e}")


def url_ok(url):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "servus-german-autopilot/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200
    except Exception:
        return False


# ---------------------------------------------------------------- planning
def plan(schedule, config):
    """Expand schedule.json into dated (post, platform) slots."""
    tz = ZoneInfo(config.get("timezone", "Europe/Vienna"))
    start = dt.date.fromisoformat(config["start_date"])
    times = config.get("times", {})
    enabled = [p for p, on in config.get("platforms", {}).items() if on]
    slots = []
    for post in schedule["posts"]:
        day = start + dt.timedelta(days=post["day"] - 1)
        hh, mm = map(int, times.get(post["kind"], "18:00").split(":"))
        local = dt.datetime(day.year, day.month, day.day, hh, mm, tzinfo=tz)
        for platform in post["platforms"]:
            if platform in enabled:
                slots.append({"key": f"{post['key']}|{platform}", "post": post, "platform": platform,
                              "due": local.astimezone(dt.timezone.utc)})
    slots.sort(key=lambda s: s["due"])
    return slots


def media_url(base, path):
    return base.rstrip("/") + "/" + path.lstrip("/")


def build_input(slot, channel_id, base, config):
    post, platform = slot["post"], slot["platform"]
    ai = bool(config.get("label_ai", True))
    if post["kind"] == "video":
        assets = [{"video": {"url": media_url(base, post["media"][0]),
                             "metadata": {"thumbnailOffset": int(post.get("thumb_ms", 700))}}}]
    else:
        imgs = post["media"]
        if platform in ("instagram", "tiktok") and len(imgs) > 10:  # both allow 10 items per carousel
            imgs = imgs[:9] + imgs[-1:]
        assets = [{"image": {"url": media_url(base, m), "metadata": {"altText": post.get("alt", post["title"])[:250]}}}
                  for m in imgs]
    meta = None
    if platform == "youtube":
        meta = {"youtube": {"title": post.get("yt_title", post["title"])[:100], "categoryId": "27",
                            "privacy": Enum("public"), "madeForKids": False, "notifySubscribers": True,
                            "isAiGenerated": ai}}
    elif platform == "instagram":
        meta = {"instagram": {"type": Enum("reel" if post["kind"] == "video" else "post"),
                              "shouldShareToFeed": True, "isAiGenerated": ai}}
    elif platform == "tiktok":
        meta = {"tiktok": ({"isAiGenerated": ai} if post["kind"] == "video" else {"title": post["title"][:90]})}
    elif platform == "pinterest":
        meta = {"pinterest": {"boardServiceId": config.get("pinterest_board_id"), "title": post["title"][:100],
                              "url": config.get("links", {}).get("shop") or None}}
    text = post["caption"]
    if platform == "youtube":
        text = post["caption"] + "\n\n" + config.get("youtube_footer", "")
    return {"channelId": channel_id, "text": text.strip(), "schedulingType": Enum("automatic"),
            "mode": Enum("customScheduled"), "dueAt": iso(slot["due"]), "assets": assets, "metadata": meta}


# ---------------------------------------------------------------- main
def main():
    dry = os.environ.get("DRY_RUN") == "1"
    config = load("config.json", {})
    schedule = load("schedule.json", {"posts": []})
    queue = load("state/queue.json", {})
    runs = load("state/runs.json", [])
    run = {"started": iso(now_utc()), "created": 0, "updated": 0, "errors": [], "warnings": [], "dry_run": dry}

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    owner, _, name = repo.partition("/")
    base = os.environ.get("PAGES_BASE") or config.get("pages_base") or (f"https://{owner}.github.io/{name}/" if repo else "")
    run["pages_base"] = base

    key = os.environ.get("BUFFER_API_KEY")
    if not key:
        run["errors"].append("BUFFER_API_KEY secret is missing — add it in the repo settings (Secrets → Actions).")
        return finish(run, runs, queue, config)

    bf = Buffer(key)
    try:
        orgs = bf.q("query { account { organizations { id name } } }")["account"]["organizations"]
        org = orgs[0]
        run["org"] = org["name"]
        chans = bf.q(f'query {{ channels(input: {{organizationId: {lit(org["id"])}}}) {{ id service name }} }}')["channels"]
    except Exception as e:
        run["errors"].append(f"Buffer login failed: {e}")
        return finish(run, runs, queue, config)

    channels = {}
    for c in chans:
        svc = str(c["service"]).lower()
        for s in SERVICES:
            if s in svc and s not in channels:
                channels[s] = c
    run["channels"] = {s: c["name"] for s, c in channels.items()}
    for s, on in config.get("platforms", {}).items():
        if on and s not in channels:
            run["warnings"].append(f"{s} is enabled in config.json but not connected in Buffer.")

    # first successful run: start tomorrow (Vienna time) unless a start date was set by hand
    if not config.get("start_date"):
        if not channels:
            run["errors"].append("No TikTok, Instagram or YouTube channel is connected in Buffer yet.")
            return finish(run, runs, queue, config)
        tz = ZoneInfo(config.get("timezone", "Europe/Vienna"))
        config["start_date"] = (now_utc().astimezone(tz).date() + dt.timedelta(days=1)).isoformat()
        save("config.json", config)
        run["warnings"].append(f"Start date set to {config['start_date']} (day 1). Change it in config.json if you like.")

    # 1) refresh status of posts we created
    refresh_status(bf, org["id"], channels, queue, run)

    # 2) top up the queue
    now = now_utc()
    horizon = now + dt.timedelta(days=int(config.get("queue_days", 7)))
    cap = int(config.get("max_queued_per_channel", 9))
    pending = {s: sum(1 for k, v in queue.items() if k.endswith("|" + s) and v.get("status") in ("scheduled", "sending")
                      and parse_iso(v.get("due")) and parse_iso(v["due"]) > now) for s in SERVICES}
    checked_urls = {}
    for slot in plan(schedule, config):
        if slot["key"] in queue and queue[slot["key"]].get("status") != "failed_to_create":
            continue
        if slot["due"] <= now + dt.timedelta(minutes=20):
            if slot["key"] not in queue:
                queue[slot["key"]] = {"due": iso(slot["due"]), "status": "missed", "platform": slot["platform"]}
            continue
        if slot["due"] > horizon:
            continue
        ch = channels.get(slot["platform"])
        if not ch:
            continue
        if pending[slot["platform"]] >= cap:
            continue
        missing = []
        for m in slot["post"]["media"]:
            u = media_url(base, m)
            if u not in checked_urls:
                checked_urls[u] = url_ok(u)
            if not checked_urls[u]:
                missing.append(u)
        if missing:
            run["errors"].append(f"{slot['key']}: media not reachable yet ({missing[0]}) — is GitHub Pages enabled?")
            continue
        inp = build_input(slot, ch["id"], base, config)
        if dry:
            run["created"] += 1
            run.setdefault("plan", []).append({"key": slot["key"], "due": iso(slot["due"])})
            continue
        mutation = ("mutation { createPost(input: " + lit(inp) + ") { "
                    "... on PostActionSuccess { post { id dueAt status } } ... on MutationError { message } } }")
        try:
            res = bf.q(mutation)["createPost"]
            if res.get("post"):
                queue[slot["key"]] = {"buffer_id": res["post"]["id"], "due": res["post"].get("dueAt") or iso(slot["due"]),
                                      "status": res["post"].get("status") or "scheduled", "platform": slot["platform"],
                                      "created": iso(now_utc())}
                pending[slot["platform"]] += 1
                run["created"] += 1
            else:
                raise RuntimeError(res.get("message") or "unknown error")
        except Exception as e:
            queue[slot["key"]] = {"due": iso(slot["due"]), "status": "failed_to_create", "platform": slot["platform"],
                                  "error": str(e)[:400]}
            run["errors"].append(f"{slot['key']}: {str(e)[:300]}")
    # 3) content runway
    last = max((s["due"] for s in plan(schedule, config)), default=None)
    if last:
        run["content_until"] = iso(last)
        days_left = (last - now).days
        if days_left < 10:
            run["warnings"].append(f"Only {max(days_left, 0)} days of content left — ask Claude for the next batch.")
    run["api_calls"] = bf.calls
    return finish(run, runs, queue, config)


def refresh_status(bf, org_id, channels, queue, run):
    ids = {v["buffer_id"]: k for k, v in queue.items() if v.get("buffer_id") and v.get("status") not in ("sent",)}
    if not ids:
        return
    chan_ids = [c["id"] for c in channels.values()]
    after, seen = None, 0
    fields = ("id status dueAt sentAt externalLink channelId error { message } "
              "metrics { type name value unit }")
    while True:
        args = f"first: 100{', after: ' + lit(after) if after else ''}"
        q = ("query { posts(" + args + ", input: " +
             lit({"organizationId": org_id, "filter": {"channelIds": chan_ids,
                  "status": [Enum("scheduled"), Enum("sending"), Enum("sent"), Enum("error")]}}) +
             ") { edges { node { " + fields + " } } pageInfo { hasNextPage endCursor } } }")
        try:
            data = bf.q(q)["posts"]
        except Exception as e:
            # metrics may not be available on every plan — retry once without them
            if "metrics" in fields:
                fields = fields.replace(" metrics { type name value unit }", "")
                continue
            run["warnings"].append(f"Could not refresh post status: {str(e)[:200]}")
            return
        for edge in data["edges"]:
            n = edge["node"]
            k = ids.get(n["id"])
            if not k:
                continue
            e = queue[k]
            before = e.get("status")
            e["status"] = n["status"]
            e["due"] = n.get("dueAt") or e.get("due")
            if n.get("sentAt"): e["sent"] = n["sentAt"]
            if n.get("externalLink"): e["link"] = n["externalLink"]
            if n.get("error"): e["error"] = (n["error"] or {}).get("message")
            if n.get("metrics"):
                e["metrics"] = {m["type"]: m["value"] for m in n["metrics"]}
            if before != e["status"]:
                run["updated"] += 1
        seen += len(data["edges"])
        if not data["pageInfo"]["hasNextPage"] or seen > 2000:
            break
        after = data["pageInfo"]["endCursor"]


def finish(run, runs, queue, config):
    run["finished"] = iso(now_utc())
    run["ok"] = not run["errors"]
    runs = ([run] + runs)[:30]
    save("state/queue.json", queue)
    save("state/runs.json", runs)
    print(json.dumps({k: v for k, v in run.items() if k != "plan"}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
