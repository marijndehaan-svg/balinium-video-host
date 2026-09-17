# balinium-video-host

Public static host for TikTok Content Planner video files, served via GitHub Pages.

Purpose: TikTok's Content Posting API (`PULL_FROM_URL`) will only fetch a video from a
URL whose domain or URL-prefix has been verified in the TikTok developer portal.
Google Drive links do not qualify. This repo satisfies that requirement with GitHub
Pages URL-prefix verification, so no DNS change on balinium.com is required.

Live base URL: `https://marijndehaan-svg.github.io/balinium-video-host/`

## Layout

```
videos/          the .mp4 files TikTok pulls from
tiktok*.txt      TikTok's URL-prefix verification file (see SETUP.md, step 2)
manifest.json    machine-readable list of hosted videos for the Content Planner
scripts/         helper to verify every hosted URL actually serves
```

## Video URL pattern

A file committed at `videos/v012-sandalwood-hook-a.mp4` is served at:

```
https://marijndehaan-svg.github.io/balinium-video-host/videos/v012-sandalwood-hook-a.mp4
```

That exact string is what goes into the Content Planner's video URL field and into
`source_info.video_url` of the TikTok API call.

## Naming rule

`v<NNN>-<product-slug>-<variant>.mp4`, lowercase, hyphens only, no spaces, no
diacritics. Example: `v007-cacao-nibs-hook-b.mp4`. The number matches the Content
Planner row ID so a video can always be traced back to its script.

## Limits worth knowing before a bulk upload

- 100 MB hard limit per file. Git rejects anything larger.
- 1 GB soft limit on total repo size. At roughly 20 MB per clip that is about 50
  videos. Past that, prune old videos or move to real object storage.
- 100 GB/month soft bandwidth limit on Pages. TikTok fetches each file once at post
  time, so this is not a realistic ceiling for this use.
- Pages serves .mp4 as `video/mp4` and supports range requests, which is what the
  TikTok fetcher needs.
- Everything here is PUBLIC and stays in git history permanently. Unlisted drafts,
  client footage, and anything not cleared for publication must not be committed.

## Who does what

- Marijn owns the repo.
- Ayesha has push access and runs the uploads and the Content Planner wiring.

See SETUP.md for the one-time setup and WINDOWS.md for the per-batch workflow.
