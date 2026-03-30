import asyncio
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml
from playwright.async_api import async_playwright, BrowserContext, Page


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def notify(title: str, message: str) -> None:
    """macOS native notification banner."""
    script = f'display notification "{message}" with title "{title}"'
    subprocess.run(["osascript", "-e", script], check=False)


async def alarm(beeps: int) -> None:
    for _ in range(beeps):
        subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], check=False)
        await asyncio.sleep(0.5)


async def dismiss_cookies(page: Page) -> None:
    candidates = [
        "Accept", "Accept all", "I agree", "Agree", "OK", "Got it",
        "Accepteren", "Alles accepteren", "Akkoord",
    ]
    for txt in candidates:
        btn = page.locator(f"button:has-text('{txt}')")
        if await btn.count() > 0:
            try:
                await btn.first.click(timeout=1200)
                return
            except Exception:
                pass


async def wait_until_ready(page: Page) -> None:
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
    except Exception:
        pass
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass


async def tickets_available(page: Page, not_available_text: str, cookie_dismissed: list[bool]) -> bool:
    await wait_until_ready(page)

    if not cookie_dismissed[0]:
        await dismiss_cookies(page)
        cookie_dismissed[0] = True

    try:
        body_text = await page.locator("body").inner_text(timeout=5000)
    except Exception:
        body_text = await page.evaluate("() => document.body ? document.body.innerText : ''")

    return not_available_text.lower() not in body_text.lower()


async def check_url(context: BrowserContext, url: str, not_available_text: str, cookie_dismissed: list[bool]) -> bool:
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return await tickets_available(page, not_available_text, cookie_dismissed)
    except Exception as e:
        print(f"[{ts()}] WARNING  {url}  {repr(e)}")
        return False
    finally:
        await page.close()


def load_urls(urls_file: str = "urls.txt") -> list[str]:
    if sys.argv[1:]:
        return sys.argv[1:]
    path = Path(urls_file)
    if not path.exists():
        print(f"ERROR: no URLs given and {urls_file} not found.")
        print("Usage: python monitor.py <url1> [url2 ...]")
        sys.exit(1)
    lines = path.read_text().splitlines()
    urls = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
    if not urls:
        print(f"ERROR: {urls_file} contains no URLs.")
        sys.exit(1)
    return urls


async def main():
    cfg = load_config()
    urls: list[str] = load_urls()
    not_available_text: str = cfg["not_available_text"]
    interval: float = cfg["interval_seconds"]
    jitter: float = cfg["jitter_seconds"]
    headless: bool = cfg["headless"]
    alarm_beeps: int = cfg["alarm_beeps"]

    # Track cookie-dismiss state per URL (persists across rounds)
    cookie_state: dict[str, list[bool]] = {url: [False] for url in urls}

    print(f"[{ts()}] Monitoring {len(urls)} URL(s):")
    for u in urls:
        print(f"  - {u}")
    print(f"\nDetection: ticket available when this text disappears:\n  '{not_available_text}'\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            locale="en-GB",
            timezone_id="Europe/Amsterdam",
        )

        while True:
            tasks = [
                check_url(context, url, not_available_text, cookie_state[url])
                for url in urls
            ]
            results = await asyncio.gather(*tasks)

            found_any = False
            for url, available in zip(urls, results):
                if available:
                    found_any = True
                    print(f"[{ts()}] TICKETS AVAILABLE  {url}")
                    notify("Ticket Alert", url)
                else:
                    print(f"[{ts()}] not yet  {url}")

            if found_any:
                await alarm(alarm_beeps)

            delay = interval + random.uniform(0, jitter)
            print(f"[{ts()}] next check in {delay:.1f}s")
            await asyncio.sleep(delay)


if __name__ == "__main__":
    asyncio.run(main())
