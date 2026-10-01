# wayglass: 15-second ad render kit

`ad.html` is the whole ad. Every frame is drawn by `render(t)`, so frames can be
rendered independently and in parallel. The GitHub workflow splits the 450 frames
(1920×1080, 30 fps) across 15 machines, synthesises the soundtrack, and gives you an MP4.

## Render it on GitHub (free)

1. **Create a new repository** on github.com. Public repos get unlimited free Actions
   minutes. Private repos work too: one render uses roughly 100–150 of the 2,000 free
   minutes per month.
2. **Upload everything in this folder** using "uploading an existing file", then commit
   to `main`. The `.github` folder is hidden on Mac. Press **Cmd+Shift+.** in Finder to
   show it before selecting everything.
   - If `.github` didn't come along: choose **Add file → Create new file**, name it
     `.github/workflows/render.yml`, and paste in the contents of `render-workflow.yml`.
3. **The render starts automatically** when you commit. You can also start it from the
   **Actions** tab: **Render wayglass ad → Run workflow**.
4. **Wait about 10 minutes**, open the finished run, and download **wayglass-ad-mp4**
   from the Artifacts section at the bottom. It's a zip containing `wayglass_ad.mp4`.

## Files

| File | What it does |
|---|---|
| `ad.html` | The ad (built, self-contained). Open it in Chrome to watch a live, non-frame-exact preview. |
| `render.py` | Captures frames with headless Chromium (`--chunk N --chunks M` renders one slice). |
| `audio.py` | Synthesises the 120 BPM soundtrack, timed to the scene cuts, to `audio.wav`. |
| `.github/workflows/render.yml` | The parallel render + encode workflow. |
| `src/` | Source for editing: `template.html` + `build.py` (run `cd src && python build.py` to rebuild `../ad.html`). |

## Render on your own computer instead

```bash
pip install playwright==1.56.0 numpy scipy
python -m playwright install chromium
python render.py            # all 450 frames into frames/
python audio.py
ffmpeg -framerate 30 -i frames/%04d.jpg -i audio.wav -c:v libx264 -crf 16 \
  -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart wayglass_ad.mp4
```

`render.py` deliberately runs Chromium's GPU path through SwiftShader. Chromium's plain
software compositor renders the 3D glass panes incorrectly, so the script stops if GPU
compositing isn't available.
