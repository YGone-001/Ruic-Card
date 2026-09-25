"""Browser acceptance test for the selectable second holographic card."""

from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
CUSTOM_BROWSER = os.environ.get("RUIC_BROWSER")
URL = "http://127.0.0.1:4173/"


def card_state(page):
    return page.evaluate(
        """() => ({
          ready: window.__holo?.ready,
          title: window.__holo?.config?.title,
          subtitle: window.__holo?.config?.subtitle,
          edition: window.__holo?.config?.edition,
          backMark: window.__holo?.config?.backMark,
          model: window.__holo?.modelSource,
          rotation: window.__holo?.root?.rotation?.toArray(),
          finish: window.__holo?.getState?.().finish,
        })"""
    )


def main() -> None:
    errors: list[str] = []
    with sync_playwright() as playwright:
        launch_options = {"headless": True}
        if CUSTOM_BROWSER:
            launch_options["executable_path"] = CUSTOM_BROWSER
        browser = playwright.chromium.launch(**launch_options)
        page = browser.new_page(viewport={"width": 1440, "height": 980}, device_scale_factor=1)
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(URL, wait_until="networkidle")
        page.wait_for_function("window.__holo && window.__holo.ready === true")
        brick_gap = card_state(page)
        assert brick_gap["title"] == "隙光", brick_gap

        page.get_by_role("button", name="02 暮途").click()
        page.wait_for_function("window.__holo?.config?.title === '暮途'")
        page.wait_for_timeout(350)
        second = card_state(page)
        assert second["subtitle"] == "落日慕思", second
        assert second["edition"] == "002 / 100", second
        assert second["backMark"] == "博", second
        assert second["model"] == "./assets/cards/sunset-drive/card.glb", second
        assert page.locator("#card-title").inner_text() == "暮途"
        assert page.locator("[data-card='sunset-drive']").get_attribute("aria-pressed") == "true"
        assert page.locator("[data-card='brick-gap']").get_attribute("aria-pressed") == "false"

        page.get_by_role("button", name="04 夏荫").click()
        page.wait_for_function("window.__holo?.config?.title === '夏荫'")
        page.wait_for_timeout(350)
        fourth = card_state(page)
        assert fourth["subtitle"] == "园游拾光", fourth
        assert fourth["edition"] == "004 / 100", fourth
        assert fourth["backMark"] == "海", fourth
        assert fourth["model"] == "./assets/cards/summer-shade/card.glb", fourth
        assert page.locator("#card-title").inner_text() == "夏荫"
        assert page.locator("[data-card='summer-shade']").get_attribute("aria-pressed") == "true"
        page.screenshot(path=str(ROOT / "verification" / "fourth-card-live.png"), full_page=True)

        page.get_by_role("button", name="02 暮途").click()
        page.wait_for_function("window.__holo?.config?.title === '暮途'")
        page.wait_for_timeout(350)

        before_drag = second["rotation"]
        stage = page.locator("#stage")
        box = stage.bounding_box()
        assert box, "stage unavailable"
        page.mouse.move(box["x"] + box["width"] * 0.45, box["y"] + box["height"] * 0.45)
        page.mouse.down()
        page.mouse.move(box["x"] + box["width"] * 0.69, box["y"] + box["height"] * 0.62, steps=8)
        page.mouse.up()
        page.wait_for_timeout(180)
        after_drag = card_state(page)["rotation"]
        assert after_drag != before_drag, (before_drag, after_drag)

        page.get_by_role("button", name="背面").click()
        page.wait_for_function("window.__holo?.getState?.().flipped === true")
        page.screenshot(path=str(ROOT / "verification" / "second-card-back.png"), full_page=True)
        page.get_by_role("button", name="正面").click()
        page.wait_for_function("window.__holo?.getState?.().flipped === false")
        page.locator("#foil").fill("0.78")
        page.locator("#foil").dispatch_event("input")
        assert page.locator("#foil-value").inner_text() == "78%"
        page.screenshot(path=str(ROOT / "verification" / "second-card-live.png"), full_page=True)

        mobile = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        mobile.goto(URL + "?card=sunset-drive", wait_until="networkidle")
        mobile.wait_for_function("window.__holo && window.__holo.ready === true")
        assert card_state(mobile)["title"] == "暮途"
        overflow = mobile.evaluate("document.documentElement.scrollWidth > innerWidth")
        assert not overflow, "mobile layout overflowed"
        mobile.screenshot(path=str(ROOT / "verification" / "second-card-mobile.png"), full_page=True)
        mobile.close()

        fourth_mobile = browser.new_page(
            viewport={"width": 390, "height": 844}, device_scale_factor=1
        )
        fourth_mobile.goto(URL + "?card=summer-shade", wait_until="networkidle")
        fourth_mobile.wait_for_function("window.__holo && window.__holo.ready === true")
        assert card_state(fourth_mobile)["title"] == "夏荫"
        overflow = fourth_mobile.evaluate("document.documentElement.scrollWidth > innerWidth")
        assert not overflow, "mobile layout overflowed"
        fourth_mobile.screenshot(
            path=str(ROOT / "verification" / "fourth-card-mobile.png"), full_page=True
        )
        fourth_mobile.close()
        browser.close()

    assert not errors, errors
    print(
        json.dumps(
            {
                "brick_gap": brick_gap,
                "second": second,
                "fourth": fourth,
                "drag_rotation": after_drag,
                "mobile_width": 390,
                "console_errors": errors,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
