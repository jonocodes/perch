import sys
import pathlib
from playwright.sync_api import sync_playwright

PROFILE = pathlib.Path(".demo-profile")
SHOTS = pathlib.Path("shots")
SHOTS.mkdir(exist_ok=True)


def login(url: str) -> None:
    PROFILE.mkdir(exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(PROFILE), headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url)
        print(f"\n[login] {url}")
        print("Log in by hand (MFA/captcha is fine). Press Enter when done...")
        input()
        ctx.close()
    print(f"[login] session saved to {PROFILE}/")


def capture(url: str, selector: str, name: str = "out") -> None:
    out = SHOTS / f"{name}.png"
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
        loc.wait_for(state="visible", timeout=20000)
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        loc.screenshot(path=str(out))
        ctx.close()
    print(f"[capture] {url}  ->  {out}  ({out.stat().st_size} bytes)")


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__ or "")
        print("usage:")
        print("  uv run demo.py login  <url>")
        print("  uv run demo.py capture <url> <selector> [name]")
        sys.exit(2)
    cmd, url = sys.argv[1], sys.argv[2]
    if cmd == "login":
        login(url)
    elif cmd == "capture":
        selector = sys.argv[3]
        name = sys.argv[4] if len(sys.argv) > 4 else "out"
        capture(url, selector, name)
    else:
        print(f"unknown command: {cmd}")
        sys.exit(2)


if __name__ == "__main__":
    main()