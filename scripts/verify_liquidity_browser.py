#!/usr/bin/env python3
"""Exercise the actual deployed GitHub Pages in desktop and mobile Chrome."""
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

STATUS = {"normal": "正常", "attention": "注意", "warning": "警戒", "unverified": "未判定"}
ARTIFACTS = Path("browser-evidence")


def canonical_json(base: str) -> dict:
    with urlopen(urljoin(base, "api/v1/liquidity/latest.json"), timeout=20) as reply:
        data = json.load(reply)
    if data.get("schema_version") != 1 or len(data.get("series", {})) < 6:
        raise AssertionError("published canonical liquidity data is missing or malformed")
    return data


def wait_for_real_values(browser, canonical: dict) -> None:
    expected_status = STATUS[canonical["assessment"]["status"]]
    wait = WebDriverWait(browser, 30)
    wait.until(lambda b: len(b.find_elements(By.CSS_SELECTOR, "#rows tr")) == 10)
    rows = browser.find_elements(By.CSS_SELECTOR, "#rows tr")
    status = browser.find_element(By.CSS_SELECTOR, "#summary strong").text
    if status != expected_status:
        raise AssertionError(f"rendered status {status!r}, canonical status {expected_status!r}")
    sofr = canonical["series"]["SOFR"]["latest"]
    first_row = rows[0]
    if first_row.find_elements(By.TAG_NAME, "td")[0].text.splitlines()[0] != "SOFR":
        raise AssertionError("first row is not SOFR")
    if f'{sofr["value"]:.2f}' not in first_row.find_elements(By.TAG_NAME, "td")[1].text:
        raise AssertionError(f'SOFR in browser does not match canonical value {sofr["value"]}')
    if sofr["date"] not in first_row.text:
        raise AssertionError("browser did not show SOFR observation date")
    # The UI now shows Japanese local time rather than raw ISO-8601 UTC.
    from datetime import datetime
    from zoneinfo import ZoneInfo
    observed_jst = datetime.fromisoformat(canonical["retrieved_at"]).astimezone(ZoneInfo("Asia/Tokyo"))
    expected_day = f"{observed_jst.year}/{observed_jst.month}/{observed_jst.day}"
    meta_text = browser.find_element(By.ID, "meta").text
    if expected_day not in meta_text or canonical["observation_cutoff"] not in meta_text:
        raise AssertionError(f"localized retrieval date or cutoff missing: {meta_text!r}")
    source_links = browser.find_elements(By.CSS_SELECTOR, "#rows td:last-child a")
    if len(source_links) != len(canonical["series"]):
        raise AssertionError(f"source link count mismatch: {len(source_links)}")
    for link in source_links:
        if not link.get_attribute("href").startswith("https://fred.stlouisfed.org/series/"):
            raise AssertionError(f"untrusted source link: {link.get_attribute('href')}")
    if len(browser.find_elements(By.CSS_SELECTOR, "#rows svg.spark")) < 6:
        raise AssertionError("historical sparklines did not render")
    if not browser.find_element(By.ID, "signals").text.strip():
        raise AssertionError("risk signals explanation is empty")


def record(browser, name: str) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    if not browser.save_screenshot(str(ARTIFACTS / name)):
        raise AssertionError(f"screenshot not created: {name}")


def run(base_url: str) -> dict:
    base = base_url.rstrip("/") + "/"
    canonical = canonical_json(base)
    driver_path = shutil.which("chromedriver")
    chrome_path = shutil.which("google-chrome") or shutil.which("google-chrome-stable") or shutil.which("chromium")
    if not driver_path or not chrome_path:
        raise RuntimeError(f"Chrome/ChromeDriver unavailable: chrome={chrome_path}, driver={driver_path}")
    options = Options()
    options.binary_location = chrome_path
    for flag in ("--headless=new", "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--window-size=1280,900"):
        options.add_argument(flag)
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    driver = webdriver.Chrome(service=Service(driver_path), options=options)
    driver.set_page_load_timeout(35)
    results: dict = {"source_commit": None, "views": [], "observation_date": canonical["series"]["SOFR"]["latest"]["date"]}
    try:
        with urlopen(urljoin(base, "deployment.json"), timeout=20) as reply:
            results["source_commit"] = json.load(reply)["source_commit"]
        # The ordinary user starts at the root, not a manually supplied deep link.
        driver.get(base)
        nav = WebDriverWait(driver, 15).until(lambda b: b.find_element(By.CSS_SELECTOR, 'nav a[href="liquidity.html"]'))
        if not nav.is_displayed():
            raise AssertionError("desktop entry to liquidity is not visible")
        nav.click()
        if not driver.current_url.rstrip("/").endswith("/liquidity.html"):
            raise AssertionError("main navigation did not open liquidity page")
        wait_for_real_values(driver, canonical)
        record(driver, "liquidity-desktop.png")
        results["views"].append({"viewport": "desktop", "width": driver.execute_script("return window.innerWidth"), "status": "passed"})

        # The mobile layout must expose a route to the view and let users scroll the wide table.
        driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
            "width": 390, "height": 844, "deviceScaleFactor": 2.75, "mobile": True,
        })
        driver.get(base)
        mobile_nav = driver.find_element(By.CSS_SELECTOR, 'nav a[href="liquidity.html"]')
        if not mobile_nav.is_displayed():
            raise AssertionError("mobile visitor cannot find liquidity navigation")
        mobile_nav.click()
        wait_for_real_values(driver, canonical)
        metrics = driver.execute_script("""const t=document.querySelector('.scroll');
            return {innerWidth:window.innerWidth, bodyWidth:document.documentElement.scrollWidth,
                    tableWidth:t.scrollWidth, tableVisible:t.clientWidth};""")
        if metrics["innerWidth"] != 390 or metrics["bodyWidth"] > 392:
            raise AssertionError(f"page overflows mobile viewport: {metrics}")
        if metrics["tableWidth"] <= metrics["tableVisible"]:
            raise AssertionError(f"mobile table horizontal scrolling is missing: {metrics}")
        scrolled = driver.execute_script("""const el=document.querySelector('.scroll');
            el.scrollLeft=el.scrollWidth;return el.scrollLeft;""")
        if scrolled <= 0:
            raise AssertionError("table cannot be horizontally scrolled on a phone")
        record(driver, "liquidity-mobile.png")

        # Follow the actual UI link, and read the JSON rather than merely checking a URL.
        driver.find_element(By.CSS_SELECTOR, 'header nav a[href="api/v1/liquidity/latest.json"]').click()
        WebDriverWait(driver, 10).until(lambda b: "source_signature" in b.find_element(By.TAG_NAME, "body").text)
        if not driver.current_url.endswith("/api/v1/liquidity/latest.json"):
            raise AssertionError("data link did not open the canonical JSON")
        driver.back()
        wait_for_real_values(driver, canonical)
        results["views"].append({"viewport": "mobile", "width": metrics["innerWidth"],
                                 "table_scrolled": scrolled, "status": "passed", "data_link": "passed"})
        return results
    except Exception:
        record(driver, "liquidity-failed.png")
        raise
    finally:
        driver.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.base_url), ensure_ascii=False))
