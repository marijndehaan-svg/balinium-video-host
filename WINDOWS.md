# Per-batch workflow (Windows)

## First time only

**1. Git for Windows** — https://git-scm.com/download/win, accept the defaults.
This also gives you Git Bash, which is where every command below runs. Not
PowerShell, not CMD.

**2. ffmpeg.** In PowerShell as administrator:

```
winget install Gyan.FFmpeg
```

Close and reopen Git Bash, then check it took:

```
ffmpeg -version
```

If `winget` is not available, download a build from
https://www.gyan.dev/ffmpeg/builds/ (get `ffmpeg-release-essentials.zip`),
unzip it to `C:\ffmpeg`, and add `C:\ffmpeg\bin` to your PATH.

**3. Clone the repo.** In Git Bash:

```
git config --global user.name "Ayesha"
git config --global user.email "<the email on your GitHub account>"
git clone https://github.com/marijndehaan-svg/balinium-video-host.git
cd balinium-video-host
```

The first push opens a browser sign-in. Use the account that got the
collaborator invite.

## Why compression is not optional

The Drive sources are phone footage, not exports. Measured on TT-20: 67 MB for
15 seconds at 38 Mbps. Committed raw, a batch of 34 would be about 2.3 GB, and
GitHub's 1 GB repo limit would stop you partway through with the oversized files
already in git history and awkward to remove.

Re-encoded, that same clip is 4.5 MB and looks identical at TikTok playback,
since TikTok re-encodes everything on ingest anyway. Compress first, always.
`prepare-batch.sh` does it for you.

## Every batch

**1. Build a manifest.** Make a file called `batch.tsv` in the repo folder, one
line per video, columns separated by spaces or tabs:

```
# id   drive-file-id                       slug
20     1-EDi8MXupIDkiy_vO-nhk8HxxVlXi_7Q   bangle-gold-bedsheet
21     1AbC2dEfGh3IjKlMn4OpQrSt5UvWxYz6    ring-silver-poolside
```

- **id** is the `ID` column in the Content Planner. `TT-20` means `20`.
- **drive-file-id** is the long string in the Drive share link, between `/d/`
  and `/view`. From `https://drive.google.com/file/d/1-EDi8MXupID.../view`
  take `1-EDi8MXupID...`. The file must be shared as "anyone with the link",
  or the download fails.
- **slug** is lowercase, hyphens only, no spaces, no diacritics. Describe the
  product and the setting so the filename reads at a glance.

Lines starting with `#` are ignored.

**2. Run it.**

```
bash scripts/prepare-batch.sh batch.tsv
```

For each row it downloads from Drive, compresses, and checks the result is
something TikTok will accept: under 100 MB, vertical, at least 3 seconds, and
faststart-enabled so the fetcher does not have to pull the whole file before it
can start reading. It prints a summary and exits non-zero if anything failed.

Sources are cached in `.work/`, which is gitignored, so re-running is cheap and
never re-downloads.

It commits nothing. Review first.

**3. Commit and push.**

```
git pull
git add videos/
git commit -m "Add batch: v020-v027"
git push
```

**4. Wait for the green check on the Actions tab**, then confirm every file
really serves:

```
bash scripts/check-urls.sh
```

Anything not showing OK is not safe to put in the planner yet. A 404 usually
just means the deploy has not landed; wait a minute and re-run.

**5. Paste each URL into the planner's `Hosted video URL` field.** The pattern is
the base URL plus the path:

```
https://marijndehaan-svg.github.io/balinium-video-host/videos/v020-bangle-gold-bedsheet.mp4
```

## Compressing a single file by hand

If you ever need one without the manifest:

```
ffmpeg -i input.mov -c:v libx264 -preset medium -crf 23 -r 30 \
       -c:a aac -b:a 128k -movflags +faststart videos/v020-my-slug.mp4
```

Higher `-crf` means smaller and slightly softer. 23 is a good default; go to 26
if a clip is still large. Do not drop `-movflags +faststart`.

## Things that will bite

- **Filenames are case-sensitive on Pages** even though they are not on Windows.
  `V020` and `v020` are different URLs. Stick to lowercase.
- **Do not commit a file over 100 MB.** Git rejects the push and cleaning it out
  of history is tedious. `prepare-batch.sh` flags this before you commit.
- **Do not rename or delete a video that a live TikTok post still references.**
- **This repo is public and git history keeps deleted files.** Nothing goes in
  here that is not cleared for publication.
- **Hosting is not approval.** A file being live at a URL does not mean the post
  is cleared. Every row still needs `Ayesha check = Looks good` (the English) and
  `Winda check = Approved` (the Bahasa) before anything goes out.
