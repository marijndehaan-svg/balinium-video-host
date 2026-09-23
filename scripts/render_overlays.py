"""
Burns the approved hook line into planner videos and hosts the result.

Picks up every TikTok Content Planner row where
    Status       = Editing
    Edit tier    = 2 Text overlay hook
    Native check = Approved          <- Winda's Bahasa check is the hard stop
    Hook (ID)    is filled
    Video file   holds a Google Drive link (shared "anyone with the link")
and for each one:
    1. downloads the source from Drive (cached in .work/),
    2. renders Hook (ID) in TikTok Sans inside TikTok's UI safe zone,
    3. writes videos/v<ID>-<slug>.mp4 (1080x1920, 30 fps, H.264, faststart),
    4. with --push: commits, pushes, waits until GitHub Pages serves the file,
       then sets Hosted video URL and moves the row to Status "Ready for QA".

Ayesha watches the hosted file and sets Status = Ready when it is good. The
hourly job in balinium-finance then sends it on (tiktok_organic.publish).

Why Pillow draws the text: Homebrew's ffmpeg has no drawtext filter. A PNG
laid over the video with ffmpeg's overlay filter looks the same on macOS,
Windows and GitHub Actions.

Usage:
    python3 scripts/render_overlays.py            # list what would be rendered
    python3 scripts/render_overlays.py --render   # render into videos/, no Notion write
    python3 scripts/render_overlays.py --push     # render, publish, update Notion
    python3 scripts/render_overlays.py --render --only 11   # one planner ID
"""
import argparse
import datetime as dt
import os
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / ".work"
OUT = ROOT / "videos"
FONT = ROOT / "fonts" / "TikTokSans-Variable.ttf"
BASE_URL = "https://marijndehaan-svg.github.io/balinium-video-host/videos/"

NOTION_API = "https://api.notion.com/v1"
PLANNER = "35305bbb-3d85-42a6-a2ab-3467ab9f1671"
WIB = dt.timezone(dt.timedelta(hours=7))

W, H = 1080, 1920
# TikTok's UI covers the top tabs, the right-hand button rail and the bottom
# caption block. The hook sits below the top tabs, clear of the right rail.
SAFE_LEFT, SAFE_RIGHT, SAFE_TOP = 90, 170, 250
MAX_LINES = 3


# -- Notion -------------------------------------------------------------------

def notion_token() -> str:
    token = os.environ.get("NOTION_TOKEN", "")
    if token:
        return token
    env = Path(os.environ.get("FINANCE_DIR", ROOT.parent / "balinium-finance")) / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("NOTION_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"')
    sys.exit("NOTION_TOKEN not set and not found in balinium-finance/.env")


def headers():
    return {"Authorization": f"Bearer {notion_token()}",
            "Notion-Version": "2025-09-03", "Content-Type": "application/json"}


def text(props, name):
    prop = props.get(name) or {}
    kind = prop.get("type")
    if kind in ("title", "rich_text"):
        return "".join(p.get("plain_text", "") for p in prop.get(kind, []))
    if kind == "select":
        return (prop.get("select") or {}).get("name", "")
    if kind == "unique_id":
        return str((prop.get("unique_id") or {}).get("number") or "")
    return ""


def drive_id(props) -> str:
    for f in (props.get("Video file") or {}).get("files", []):
        url = (f.get("external") or {}).get("url") or f.get("name") or ""
        m = re.search(r"/d/([A-Za-z0-9_-]{20,})", url) or re.search(r"id=([A-Za-z0-9_-]{20,})", url)
        if m:
            return m.group(1)
    return ""


def due_rows():
    body = {"page_size": 100, "filter": {"and": [
        {"property": "Status", "select": {"equals": "Editing"}},
        {"property": "Edit tier", "select": {"equals": "2 Text overlay hook"}},
        {"property": "Native check", "select": {"equals": "Approved"}},
        {"property": "Hook (ID)", "rich_text": {"is_not_empty": True}},
    ]}, "sorts": [{"property": "Publish at", "direction": "ascending"}]}
    resp = requests.post(f"{NOTION_API}/data_sources/{PLANNER}/query",
                         headers=headers(), json=body, timeout=30)
    resp.raise_for_status()
    rows = []
    for page in resp.json()["results"]:
        p = page["properties"]
        if text(p, "Notes").startswith("RENDER PROBLEM"):
            continue  # waits until a person fixes it and deletes that line
        rows.append({
            "id": page["id"],
            "num": text(p, "ID"),
            "title": text(p, "Video"),
            "hook": text(p, "Hook (ID)").strip(),
            "notes": text(p, "Notes").strip(),
            "drive": drive_id(p),
        })
    return rows


def mark_ready_for_qa(row, url, note=""):
    stamp = dt.datetime.now(WIB).strftime("%d %b %H:%M")
    line = (f"OVERLAY RENDERED {stamp} WIB: hook burned in, file at Hosted video URL. {note} "
            f"Ayesha: watch it, then set Status = Ready (or back to Editing with a note).").replace("  ", " ")
    notes = (line + ("\n\n" + row["notes"] if row["notes"] else ""))[:1990]
    resp = requests.patch(f"{NOTION_API}/pages/{row['id']}", headers=headers(), timeout=30, json={
        "properties": {
            "Hosted video URL": {"url": url},
            "Status": {"select": {"name": "Ready for QA"}},
            "Notes": {"rich_text": [{"text": {"content": notes}}]},
        }})
    resp.raise_for_status()


def flag_problem(row, message):
    stamp = dt.datetime.now(WIB).strftime("%d %b %H:%M")
    line = f"RENDER PROBLEM {stamp} WIB: {message} Fix it, then delete this line to retry."
    notes = (line + ("\n\n" + row["notes"] if row["notes"] else ""))[:1990]
    requests.patch(f"{NOTION_API}/pages/{row['id']}", headers=headers(), timeout=30,
                   json={"properties": {"Notes": {"rich_text": [{"text": {"content": notes}}]}}})


# -- Drive --------------------------------------------------------------------

def download(file_id: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 100_000:
        return True
    s = requests.Session()
    url = "https://drive.usercontent.google.com/download"
    r = s.get(url, params={"id": file_id, "export": "download", "confirm": "t"},
              stream=True, timeout=120)
    if "text/html" in r.headers.get("content-type", ""):
        return False  # not shared publicly, or a wrong id
    with open(dest, "wb") as fh:
        for chunk in r.iter_content(1 << 20):
            fh.write(chunk)
    return dest.stat().st_size > 100_000


# -- Rendering ----------------------------------------------------------------

def font(size, weight="Bold"):
    f = ImageFont.truetype(str(FONT), size)
    f.set_variation_by_name(weight)
    return f


def wrap(draw, words, fnt, max_w):
    lines, line = [], ""
    for word in words:
        trial = f"{line} {word}".strip()
        if not line or draw.textlength(trial, font=fnt) <= max_w:
            line = trial
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def hook_png(hook: str, out: Path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    max_w = W - SAFE_LEFT - SAFE_RIGHT - 2 * 30
    for size in range(78, 42, -4):
        fnt = font(size)
        lines = wrap(draw, hook.split(), fnt, max_w)
        if len(lines) <= MAX_LINES and all(draw.textlength(l, font=fnt) <= max_w for l in lines):
            break
    ascent, descent = fnt.getmetrics()
    line_h = ascent + descent
    pad_x, pad_y, gap = 30, 14, 12
    centre = SAFE_LEFT + (W - SAFE_LEFT - SAFE_RIGHT) // 2
    y = SAFE_TOP
    for line in lines:
        tw = draw.textlength(line, font=fnt)
        x = centre - tw / 2
        draw.rounded_rectangle((x - pad_x, y - pad_y, x + tw + pad_x, y + line_h + pad_y),
                               radius=20, fill=(255, 255, 255, 240))
        draw.text((x, y), line, font=fnt, fill=(18, 18, 18, 255))
        y += line_h + 2 * pad_y + gap
    img.save(out)


def probe(path: Path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                          "-show_entries", "stream=width,height:stream_side_data=rotation:format=duration",
                          "-of", "default=nw=1", str(path)], capture_output=True, text=True).stdout
    vals = dict(l.split("=", 1) for l in out.split() if "=" in l)
    w, h = int(vals.get("width", 0)), int(vals.get("height", 0))
    # Phones store portrait video as landscape plus a rotation flag; ffmpeg
    # applies the flag when rendering, so the check must too.
    if abs(int(float(vals.get("rotation", 0) or 0))) == 90:
        w, h = h, w
    return w, h, float(vals.get("duration", 0) or 0)


def render(src: Path, png: Path, out: Path, boomerang=False):
    # Fill 9:16 (scale to cover, centre crop), then lay the hook on top.
    # boomerang: clips under TikTok's 3-second minimum play forward then
    # backward, which doubles them without a jump cut. The reverse runs after
    # the downscale, so it buffers 1080p frames, not 4K ones.
    base = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"setsar=1,fps=30")
    if boomerang:
        vf = (f"{base},split[f][r0];[r0]reverse[r];[f][r]concat=n=2:v=1:a=0[b];"
              f"[b][1:v]overlay=0:0,format=yuv420p[v]")
        audio = ["-an"]  # the source audio would play backwards; the sound is added in TikTok
    else:
        vf = f"{base}[b];[b][1:v]overlay=0:0,format=yuv420p[v]"
        audio = ["-map", "0:a?", "-c:a", "aac", "-b:a", "128k"]
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-i", str(png),
           "-filter_complex", vf, "-map", "[v]", *audio,
           "-c:v", "libx264", "-preset", "medium", "-crf", "23",
           # TikTok re-encodes on upload; the cap keeps noisy 4K sources from
           # filling this repo's 1 GB soft limit (TT-27 was 49 MB uncapped).
           "-maxrate", "6M", "-bufsize", "12M",
           "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)


def slug(title: str) -> str:
    t = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:40].rstrip("-")


# -- Main ---------------------------------------------------------------------

def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True).stdout


def wait_served(url: str, size: int, timeout=600) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            r = requests.head(url, timeout=20)
            if r.status_code == 200 and int(r.headers.get("content-length", 0)) == size:
                return True
        except requests.RequestException:
            pass
        time.sleep(15)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true", help="render into videos/ (no Notion write)")
    ap.add_argument("--push", action="store_true", help="render, commit, push, update Notion")
    ap.add_argument("--only", help="planner ID to render (e.g. 11)")
    args = ap.parse_args()
    WORK.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)

    rows = due_rows()
    if args.only:
        rows = [r for r in rows if r["num"] == args.only]
    if not rows:
        print("Nothing to render.")
        return
    done, problems = [], []
    for row in rows:
        name = f"v{int(row['num']):03d}-{slug(row['title'])}.mp4"
        label = f"TT-{row['num']} {row['title'][:45]}"
        if not row["drive"]:
            problems.append(f"{label}: no Google Drive link in Video file")
            if args.push:
                flag_problem(row, "No Google Drive link in Video file.")
            continue
        if not (args.render or args.push):
            print(f"WOULD RENDER {label} -> {name} | hook: {row['hook']}")
            continue
        src = WORK / f"{name}.src"
        if not download(row["drive"], src):
            problems.append(f"{label}: Drive download refused (share it as 'anyone with the link')")
            if args.push:
                flag_problem(row, "Drive refused the download: share the file as 'anyone with the link'.")
            continue
        w, h, dur = probe(src)
        if dur < 1.5:
            problems.append(f"{label}: source is {dur:.1f}s, too short even played forward and back")
            if args.push:
                flag_problem(row, f"Source is {dur:.1f}s; TikTok needs 3s even played forward and back.")
            continue
        boomerang = dur < 3
        png = WORK / f"{name}.hook.png"
        hook_png(row["hook"], png)
        out = OUT / name
        render(src, png, out, boomerang=boomerang)
        note = ""
        if boomerang:
            note += f" Source was {dur:.1f}s (TikTok needs 3s), so it plays forward then backward ({2 * dur:.1f}s)."
        if w > h:
            note += " Landscape source, centre-cropped to 9:16: check the jewelry is in frame."
        print(f"RENDERED {label} -> {name} ({out.stat().st_size / 1_048_576:.1f} MB){note}")
        done.append((row, name, out.stat().st_size, note.strip()))

    if args.push and done:
        git("add", *[f"videos/{n}" for _, n, _, _ in done])
        git("commit", "-m", f"Render {len(done)} planner video(s) with burned-in hook")
        for attempt in range(4):  # large uploads time out on a slow line (HTTP 408, 23 Sep)
            try:
                git("-c", "http.postBuffer=524288000", "push", "-q", "origin", "HEAD")
                break
            except subprocess.CalledProcessError:
                if attempt == 3:
                    raise
                time.sleep(30)
        repo = os.environ.get("GITHUB_REPOSITORY")
        if repo and os.environ.get("GH_TOKEN"):
            # A push made with the Actions token may not start a Pages build.
            subprocess.run(["gh", "api", "-X", "POST", f"repos/{repo}/pages/builds"],
                           capture_output=True)
        for row, name, size, note in done:
            url = BASE_URL + name
            if wait_served(url, size):
                mark_ready_for_qa(row, url, note)
                print(f"QA     TT-{row['num']} -> Ready for QA, {url}")
            else:
                problems.append(f"TT-{row['num']}: pushed but Pages did not serve {name} within 10 min; row not updated")
    for p in problems:
        print(f"PROBLEM {p}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
