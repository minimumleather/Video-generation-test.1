"""Render frames of ad.html (deterministic render(t)) with headless Chromium.

Usage:
  python render.py                       # all 450 frames
  python render.py --chunk 3 --chunks 15 # just one slice (used by the GitHub workflow)
"""
import argparse, asyncio, math, os, pathlib, sys, time
from playwright.async_api import async_playwright

FPS, DURATION = 30, 15
TOTAL = FPS * DURATION

# GPU compositing through SwiftShader. Without these flags Chromium's software
# compositor mis-renders backdrop-filter on 3D-transformed glass (truncated panes).
CHROME_ARGS = [
    "--force-color-profile=srgb", "--allow-file-access-from-files",
    "--use-angle=swiftshader", "--use-gl=angle", "--enable-unsafe-swiftshader",
    "--ignore-gpu-blocklist", "--enable-gpu",
]

async def main(a):
    per = math.ceil(TOTAL / a.chunks)
    start, end = a.chunk * per, min(TOTAL, (a.chunk + 1) * per)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    page_url = pathlib.Path(__file__).with_name("ad.html").resolve().as_uri() + "?capture"
    print(f"chunk {a.chunk}/{a.chunks}: frames {start}..{end - 1}", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=CHROME_ARGS)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        page.on("pageerror", lambda e: print("PAGE ERROR:", e, flush=True))
        await page.goto(page_url)
        await page.wait_for_function("window.__ready === true", timeout=120_000)
        gl = await page.evaluate("""(() => { const g = document.createElement('canvas').getContext('webgl');
            if (!g) return 'none'; const d = g.getExtension('WEBGL_debug_renderer_info');
            return d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : 'webgl'; })()""")
        print("GPU renderer:", gl, flush=True)
        if "SwiftShader" not in gl and not a.allow_software:
            sys.exit("GPU compositing is unavailable, so the glass would render incorrectly. "
                     "Re-run with --allow-software to render anyway.")
        # warm-up frame so filters/images are decoded before the first saved frame
        await page.evaluate(f"render({start / FPS})")
        await page.screenshot(type="jpeg", quality=50)
        t0 = time.time()
        for i in range(start, end):
            await page.evaluate(f"render({i / FPS})")
            await page.screenshot(path=str(out / f"{i:04d}.jpg"), type="jpeg", quality=95)
            done = i - start + 1
            eta = (time.time() - t0) / done * (end - start - done)
            print(f"frame {i:04d}  ({done}/{end - start}, ~{eta / 60:.1f} min left)", flush=True)
        await browser.close()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", type=int, default=0)
    ap.add_argument("--chunks", type=int, default=1)
    ap.add_argument("--out", default="frames")
    ap.add_argument("--allow-software", action="store_true")
    asyncio.run(main(ap.parse_args()))
