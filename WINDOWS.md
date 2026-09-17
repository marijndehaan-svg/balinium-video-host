# Per-batch workflow (Windows)

## First time only

Install Git for Windows: https://git-scm.com/download/win
Accept the defaults. Then in Git Bash:

```
git config --global user.name "Ayesha"
git config --global user.email "<the email on her GitHub account>"
git clone https://github.com/marijndehaan-svg/balinium-video-host.git
cd balinium-video-host
```

The first push opens a browser sign-in. Use the account that received the
collaborator invite.

## Every batch

1. Drop the .mp4 files into the `videos\` folder, named per the rule in README.md.
2. In the repo folder:

```
git pull
git add videos/
git commit -m "Add batch: v012-v019"
git push
```

3. Wait for the green check on the Actions tab, then verify one file really serves
   before wiring it into the planner:

```
curl -I https://marijndehaan-svg.github.io/balinium-video-host/videos/v012-sandalwood-hook-a.mp4
```

Expect `HTTP/2 200` and `content-type: video/mp4`. A 404 means the deploy has not
landed or the filename does not match exactly. Filenames are case-sensitive on Pages
even though they are not on Windows, so `V012` and `v012` are different URLs.

4. Put the URL in the Content Planner row.

## Checking a whole batch at once

From the repo folder in Git Bash:

```
bash scripts/check-urls.sh
```

It prints the status for every file in `videos/`. Anything not 200 is not safe to
hand to TikTok.

## Things that will bite

- Do not commit a file over 100 MB. Git rejects the push and the cleanup is
  tedious. Compress first.
- Do not rename or delete a video that a live TikTok post still references.
- Do not commit anything not cleared for publication. The repo is public and git
  history keeps deleted files.
