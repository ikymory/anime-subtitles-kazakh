"""Optional real-browser acceptance for a staged public directory.

Install Playwright separately and run `python -m playwright install chromium`.
The API itself and the unittest suite have no third-party dependencies.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def smoke(directory: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "subtitle_api.server",
            "--directory",
            str(directory.resolve()),
            "--port",
            "0",
        ],
        cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    try:
        startup = server.stdout.readline().strip()
        if not startup.startswith("Subtitle API: http://127.0.0.1:"):
            raise RuntimeError("Local API failed to start: " + startup)
        origin = startup.removeprefix("Subtitle API: ")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin, wait_until="domcontentloaded")
            page.wait_for_selector("#mainAnimeGrid [data-anime-slug]", timeout=30000)
            page.evaluate(
                "clearInterval(heroTimer); currentHeroIndex=0; updateHeroDisplay(true)"
            )
            measured = page.evaluate("fetch('api/v1/stats.json').then(r=>r.json())")
            language_counts = {}
            for lang in ("kk", "en", "ja"):
                page.evaluate("lang => setLanguage(lang)", lang)
                footer = page.locator("#footerSubText").inner_text()
                assert str(measured["total_episodes"]) in footer.replace(",", ""), (
                    footer
                )
                language_counts[lang] = footer
            page.evaluate("setLanguage('en')")
            fallback = page.evaluate(
                "getAnimeDescription({slug:'example',title:{english:'A & B'},available_episodes_count:2},'en')"
            )
            assert "complete" not in fallback and "A & B" in fallback, fallback
            page.screenshot(path=str(output / "catalog-desktop.png"))
            page.locator("#searchInput").fill("frieren")
            page.wait_for_function(
                "document.querySelectorAll('#mainAnimeGrid [data-anime-slug]').length < 10"
            )
            page.locator('#mainAnimeGrid [data-anime-slug="frieren"]').focus()
            page.keyboard.press("Enter")
            page.wait_for_selector("#modalEpisodesList a")
            manifest = page.evaluate(
                "fetch('api/v1/anime/frieren.json').then(r=>r.json())"
            )
            rows = page.locator("#modalEpisodesList > div").count()
            assert rows == len(manifest["subtitles"])
            links = page.locator("#modalEpisodesList a").evaluate_all(
                '(links)=>links.slice(0,3).map(a=>({text:a.textContent,href:a.getAttribute("href")}))'
            )
            for link in links:
                response = page.request.get(origin + "/" + link["href"])
                assert response.ok, link
                assert response.headers.get("access-control-allow-origin") == "*"
            assert ".ass" not in page.locator("#modalEpSubtitleText").inner_text()
            page.screenshot(path=str(output / "catalog-downloads.png"))
            vtt = next(
                track["assets"]["vtt"]
                for track in manifest["subtitles"]
                if track["files"].get("vtt")
            )
            player = browser.new_page()
            player.goto(origin + "/api.html", wait_until="domcontentloaded")
            cue_count = player.evaluate(
                """async path => {
              const video = document.createElement('video');
              const track = document.createElement('track');
              video.crossOrigin = 'anonymous';
              track.kind = 'subtitles'; track.src = path;
              try { return await new Promise((resolve,reject) => {
                const timeout = setTimeout(()=>reject(new Error('WebVTT load timed out: '+JSON.stringify({track:track.readyState,mode:track.track.mode,cues:track.track.cues?.length,video:video.readyState,error:video.error?.message,src:track.src}))),10000);
                track.onload=()=>{clearTimeout(timeout);resolve(track.track.cues.length);};
                track.onerror=()=>{clearTimeout(timeout);reject(new Error('WebVTT rejected by browser'));};
                track.default = true; video.append(track); document.body.append(video); track.track.mode = 'hidden';
              }); } finally {video.remove();}
            }""",
                vtt["path"],
            )
            assert cue_count == vtt["cues"], (cue_count, vtt["cues"])
            player.close()
            page.keyboard.press("Escape")
            assert page.locator("#animeModal").is_hidden()
            assert page.locator('#mainAnimeGrid [data-anime-slug="frieren"]').evaluate(
                "(el)=>el===document.activeElement"
            )
            mobile = {}
            for width in (390, 320):
                page.set_viewport_size({"width": width, "height": 844})
                for lang in ("kk", "en", "ja"):
                    page.evaluate("lang=>setLanguage(lang)", lang)
                    mobile[f"{width}-{lang}"] = page.evaluate(
                        "document.documentElement.scrollWidth <= innerWidth"
                    )
                page.evaluate("setLanguage('en')")
                page.evaluate("window.scrollTo(0,0)")
                assert page.evaluate(
                    """[...document.querySelectorAll('#siteHeader button,#siteHeader a')].filter(el=>el.getClientRects().length).every(el=>el.getBoundingClientRect().bottom<=document.querySelector('#siteHeader').getBoundingClientRect().bottom+1)"""
                ), "Mobile header overlaps the page"
                page.screenshot(path=str(output / f"catalog-mobile-{width}.png"))
            assert all(mobile.values()), mobile
            page.goto(origin + "/api.html", wait_until="domcontentloaded")
            page.locator("#run").click()
            page.wait_for_function(
                "document.getElementById('status').textContent.includes('OK')"
            )
            assert (
                str(measured["total_episodes"])
                in page.locator("#response").inner_text()
            )
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.evaluate("window.scrollTo(0,0)")
            page.screenshot(path=str(output / "api-mobile.png"))
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.screenshot(path=str(output / "api-desktop.png"))
            assert not errors, errors
            result = {
                "page_errors": errors,
                "language_counts": language_counts,
                "frieren_rows": rows,
                "first_downloads": links,
                "browser_webvtt_cues": cue_count,
                "mobile_fits": mobile,
                "api_explorer": "200 OK",
            }
            (output / "browser-verification.json").write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            browser.close()
            return result
    finally:
        server.terminate()
        server.communicate(timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(".build/pages"))
    parser.add_argument("--output", type=Path, default=Path(".build/browser"))
    args = parser.parse_args()
    print(json.dumps(smoke(args.directory, args.output)))


if __name__ == "__main__":
    main()
