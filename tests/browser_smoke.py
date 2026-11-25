"""Exercise the built starter at a project subpath in Chromium."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import tempfile
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    screenshots = ROOT / "browser-checks"
    screenshots.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        shutil.copytree(ROOT / "dist", Path(temporary) / "example-tool")
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=temporary))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1280, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}/example-tool/")
                page.locator("#edition option[value='31383021405025']").wait_for(state="attached")
                page.locator("#edition").select_option("31383021405025")
                page.locator("#query").fill("520 Granville")
                page.locator("#search-button").click()
                page.locator("#results .card").first.wait_for()
                assert "520 Granville" in page.locator("#results").inner_text()
                assert "/page/n11/mode/1up" in page.locator("#results .links a").first.get_attribute("href")
                page.locator("#results button[aria-pressed]").first.click()
                page.reload()
                page.locator("#show-saved").click()
                assert page.locator("#results .card").count() == 1
                with page.expect_download() as download:
                    page.locator("#export").click()
                assert download.value.suggested_filename.endswith(".csv")
                page.locator("#clear-saved").click()
                assert "No evidence saved" in page.locator("#results").inner_text()
                page.locator("#city").select_option("Halifax")
                page.locator("#edition").select_option("cihm_36247")
                page.locator("#query").fill("Barrington")
                page.locator("#search-button").click()
                page.locator("#results .card").first.wait_for()
                assert "Barrington" in page.locator("#results").inner_text()
                page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)
                assert not errors, errors
                browser.close()
            print("Browser checks passed: subpath, real directory searches, exact scan, saved evidence, CSV and mobile layout")
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
