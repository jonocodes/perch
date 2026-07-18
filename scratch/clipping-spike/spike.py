import os
import pathlib
from playwright.sync_api import sync_playwright

PROFILE = pathlib.Path(".demo-profile")
SHOTS = pathlib.Path("shots")
SHOTS.mkdir(exist_ok=True)

url = "https://example.com"
selector = "div"
out = SHOTS / "example.png"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        str(PROFILE),
        headless=True,
        viewport={"width": 1280, "height": 900},
        device_scale_factor=2,
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(url, wait_until="domcontentloaded")
    loc = page.locator(selector).first
    loc.wait_for(state="visible", timeout=15000)
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    loc.screenshot(path=str(out))
    print(f"saved {out}  ({out.stat().st_size} bytes)")
    ctx.close()