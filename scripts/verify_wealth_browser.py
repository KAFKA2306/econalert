#!/usr/bin/env python3
"""Verify the deployed wealthy-consumer Pages flow with desktop and mobile Chrome."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import urlopen

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


def verify_cards(browser, canonical: dict) -> None:
    count = len(canonical["indicators"])
    WebDriverWait(browser, 25).until(
        lambda b: len(b.find_elements(By.CSS_SELECTOR, "#cards article.card")) == count
    )
    for indicator in canonical["indicators"]:
        card = browser.find_element(By.XPATH, "//article[@class='card'][.//div[contains(@class,'name') and text()=" + json.dumps(indicator["name"], ensure_ascii=False) + "]]")
        if indicator["period"] not in card.text or indicator["released_at"] not in card.text:
            raise AssertionError(f"period/release missing for {indicator['id']}")
        link = card.find_element(By.CSS_SELECTOR, "footer a.source")
        if link.get_attribute("href") != indicator["source_url"]:
            raise AssertionError(f"source mismatch: {indicator['id']}")
        if link.get_attribute("target") != "_blank":
            raise AssertionError("source link should open separately")


def click_filter(browser, category: str, expected: int) -> None:
    button = browser.find_element(By.CSS_SELECTOR, "button[data-cat='" + category + "']")
    button.click()
    WebDriverWait(browser, 8).until(
        lambda b: len(b.find_elements(By.CSS_SELECTOR, "#cards article.card")) == expected
    )
    if button.get_attribute("aria-pressed") != "true":
        raise AssertionError("filter selection not exposed to assistive technology")


def entry(browser, base: str, canonical: dict) -> None:
    browser.get(base)
    launch = WebDriverWait(browser, 15).until(
        lambda b: b.find_element(By.CSS_SELECTOR, 'a[href="wealth.html"]')
    )
    if not launch.is_displayed():
        raise AssertionError("ordinary homepage entry is invisible")
    launch.click()
    if not browser.current_url.endswith("/wealth.html"):
        raise AssertionError("homepage entry did not open wealth view")
    verify_cards(browser, canonical)


def capture(browser, path: str) -> None:
    Path("browser-evidence").mkdir(exist_ok=True)
    if not browser.save_screenshot("browser-evidence/" + path):
        raise AssertionError("could not capture " + path)


def run(base_url: str) -> dict:
    base = base_url.rstrip("/") + "/"
    with urlopen(urljoin(base, "api/v1/wealth-consumption/latest.json"), timeout=20) as response:
        canonical = json.load(response)
    if canonical.get("schema_version") != 1 or len(canonical.get("indicators", [])) != 6:
        raise AssertionError("public research dataset malformed")
    options = Options()
    options.binary_location = shutil.which("google-chrome") or shutil.which("google-chrome-stable") or shutil.which("chromium")
    for flag in ("--headless=new", "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--window-size=1280,900"):
        options.add_argument(flag)
    browser = webdriver.Chrome(service=Service(shutil.which("chromedriver")), options=options)
    browser.set_page_load_timeout(35)
    results = {"indicator_count": len(canonical["indicators"]), "views": []}
    try:
        entry(browser, base, canonical)
        for cat,count in [("luxury",3),("housing",2),("spending",1),("all",6)]:
            click_filter(browser, cat, count)
        capture(browser, "wealth-desktop.png")
        results["views"].append({"viewport": "desktop", "entry": "passed", "filters": "passed"})

        browser.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
            "width": 390, "height": 844, "deviceScaleFactor": 2.75, "mobile": True
        })
        entry(browser, base, canonical)
        sizes = browser.execute_script(
            "return {viewport:window.innerWidth,page:document.documentElement.scrollWidth};"
        )
        if sizes["viewport"] != 390 or sizes["page"] > 392:
            raise AssertionError(f"mobile viewport overflow: {sizes}")
        for cat,count in [("housing",2),("spending",1),("all",6)]:
            click_filter(browser, cat, count)
        capture(browser, "wealth-mobile.png")

        # Follow the actual on-page JSON link, then return to the rendered dashboard.
        browser.find_element(By.CSS_SELECTOR, 'a[href="api/v1/wealth-consumption/latest.json"]').click()
        WebDriverWait(browser, 10).until(
            lambda b: "wealthy-consumer" in b.find_element(By.TAG_NAME, "body").text
        )
        if not browser.current_url.endswith("/api/v1/wealth-consumption/latest.json"):
            raise AssertionError("JSON link navigated to the wrong path")
        browser.back()
        verify_cards(browser, canonical)
        results["views"].append({"viewport": "mobile", "entry": "passed",
                                 "filters": "passed", "json_link": "passed"})
        return results
    except Exception:
        capture(browser, "wealth-failed.png")
        raise
    finally:
        browser.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.base_url), ensure_ascii=False))
