# One-time setup

## 1. Repo and Pages

Public repo, GitHub Pages enabled on branch `main`, folder `/` (root).
Base URL: `https://marijndehaan-svg.github.io/balinium-video-host/`

Confirm it is live:

```
curl -I https://marijndehaan-svg.github.io/balinium-video-host/
```

Expect `HTTP/2 200`. The first deploy can take up to 10 minutes.

Status as of 17 Sep 2026: live and serving. Verified that `/manifest.json` and
`/videos/` both return 200.

## 2. TikTok URL-prefix verification (Ayesha)

Status as of 18 Sep 2026: DONE. `python -m tiktok_organic.property list` shows this
prefix as `type=url_prefix status=verified`; the verification file is
`tiktokjLgyZrHblOkdwaE7GMrxhrjc6fTiq6zi.txt` in the repo root and must stay there.
The steps below are kept for the next prefix or a re-verify.

One correction before starting. The token that was circulated,
`tiktok-developers-site-verification=htiUQEMKrv7FP2MzWuZvqYui11LZ3xOd`, is the
**signature of a different property**: the `balinium.com` **domain** property
already registered on the "balinium-organic" app (status: unverified/pending
as of 18 Sep 2026), confirmed live via `/business/property/list/`. It does not
carry over to this URL prefix -- a URL-prefix property gets its own signature
and its own file name once it is added. Do not reuse the balinium.com token
for this repo's prefix.

### Primary path: the API, from balinium-finance

`tiktok_organic/property.py` in the `balinium-finance` repo wraps
`/business/property/add/` and `/business/property/verify/` in a small CLI. It
defaults to a dry run (prints exactly what it would send, nothing more) and
only calls the API with `--yes`.

```
cd ~/Documents/balinium-finance

# 1. dry run first -- confirm the URL and type are right before sending anything
python -m tiktok_organic.property add \
  --url https://marijndehaan-svg.github.io/balinium-video-host/ --type url_prefix

# 2. add for real
python -m tiktok_organic.property add \
  --url https://marijndehaan-svg.github.io/balinium-video-host/ --type url_prefix --yes
```

This prints the `signature` and `file_name` TikTok generated. Then do steps
4-6 below to host the file, and finally:

```
python -m tiktok_organic.property verify \
  --url https://marijndehaan-svg.github.io/balinium-video-host/ --type url_prefix --yes
```

`python -m tiktok_organic.property list` is read-only and safe to run any
time to check what is currently registered and its status.

### Fallback: the portal, by hand

If the API route is unavailable, the same steps work by hand:

1. TikTok for Developers, your app, Manage apps, URL properties.
2. Add property, choose **URL prefix** (not Domain), and enter exactly:
   `https://marijndehaan-svg.github.io/balinium-video-host/`
   The trailing slash matters. TikTok will only accept video URLs that start with
   this exact prefix.
3. Choose the **verification file** method. Download the file TikTok generates. It is
   named like `tiktokXXXXXXXXXXXX.txt` and contains one line:
   `tiktok-developers-site-verification=<token>`

### 4-7. Host the file and verify (both paths)

4. Put that file in the ROOT of this repo, next to README.md, not in `videos/`.
5. Commit and push:
   ```
   git add tiktok*.txt
   git commit -m "Add TikTok URL-prefix verification file"
   git push
   ```
6. Wait for the Pages deploy to finish (Actions tab, green check), then confirm the
   file is actually served:
   ```
   curl https://marijndehaan-svg.github.io/balinium-video-host/tiktokXXXXXXXXXXXX.txt
   ```
   It must return the token line, not an HTML 404. If you get the 404 page, the
   deploy has not landed yet.
7. Verify: via the API command above, or in the portal, click Verify.

If verification fails, the cause is nearly always one of: the deploy had not
finished, the file landed in a subfolder, or the prefix was entered without the
trailing slash.

## 3. Push access

Ayesha is a collaborator with push rights. She has to accept the emailed invite
before her first push will work.

## 4. What this does not solve

Hosting removes the fetch-URL blocker only. The 32 scripted rows are all sitting at
`Native check = Needed` and stay unpostable until Winda signs off on the Bahasa copy.
That gate is a human approval on public-facing copy and should not be automated away
just because the pipeline is now technically able to post.
