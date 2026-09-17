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

One correction before starting. The token that was circulated,
`tiktok-developers-site-verification=htiUQEMKrv7FP2MzWuZvqYui11LZ3xOd`, is the token
TikTok issued for the **DNS TXT record** route on balinium.com. Do not assume it
carries over to this route. URL-prefix verification issues its own token and its own
filename. Get the real one from the portal:

1. TikTok for Developers, your app, Manage apps, URL properties.
2. Add property, choose **URL prefix** (not Domain), and enter exactly:
   `https://marijndehaan-svg.github.io/balinium-video-host/`
   The trailing slash matters. TikTok will only accept video URLs that start with
   this exact prefix.
3. Choose the **verification file** method. Download the file TikTok generates. It is
   named like `tiktokXXXXXXXXXXXX.txt` and contains one line:
   `tiktok-developers-site-verification=<token>`
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
7. Back in the portal, click Verify.

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
