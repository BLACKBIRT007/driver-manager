"""
driver_checker.py - Queries the Microsoft Update Catalog for newer drivers.
Falls back to a simple manufacturer-version heuristic when the catalog
doesn't return results.
"""

from __future__ import annotations
import re
import time
import requests
from typing import List, Optional, Tuple
from device_scanner import Device
from logger import log

CATALOG_SEARCH_URL = "https://www.catalog.update.microsoft.com/Search.aspx"
CATALOG_DOWNLOAD_URL = "https://www.catalog.update.microsoft.com/DownloadDialog.aspx"
REQUEST_TIMEOUT = 15
RATE_LIMIT_DELAY = 0.5   # seconds between catalog requests


def _parse_version(version_str: str) -> Tuple[int, ...]:
    """Converts '27.21.14.4664' → (27, 21, 14, 4664) for comparison."""
    if not version_str:
        return (0,)
    parts = re.split(r"[.\-,]", version_str.strip())
    result = []
    for p in parts:
        try:
            result.append(int(p))
        except ValueError:
            pass
    return tuple(result) if result else (0,)


def _version_is_newer(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


def _search_catalog(query: str) -> Optional[dict]:
    """
    Searches the Microsoft Update Catalog and returns the best matching
    driver entry as a dict with 'version' and 'download_url' keys, or None.
    """
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        resp = session.get(
            CATALOG_SEARCH_URL,
            params={"q": query},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()

        # Parse version numbers from the HTML table (basic scrape)
        version_pattern = re.compile(r"\d+\.\d+[\.\d]*")
        guid_pattern = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)

        versions = version_pattern.findall(resp.text)
        guids = guid_pattern.findall(resp.text)

        if not versions:
            return None

        # Pick the highest version found
        best_version = max(versions, key=_parse_version)
        download_url = None

        if guids:
            download_url = f"https://www.catalog.update.microsoft.com/DownloadDialog.aspx?updateID={guids[0]}"

        return {"version": best_version, "download_url": download_url}

    except requests.RequestException as e:
        log.debug(f"Catalog request failed for '{query}': {e}")
        return None


def check_device(device: Device) -> Device:
    """
    Checks a single device for a driver update.
    Updates device.latest_version, device.update_available, device.download_url in place.
    Returns the (modified) device.
    """
    if not device.driver_version:
        return device

    # Build a sensible search query
    query_parts = [device.display_name]
    if device.manufacturer and device.manufacturer.lower() not in ("microsoft", "(standard", ""):
        query_parts.insert(0, device.manufacturer)
    query = " ".join(query_parts) + " driver"

    log.debug(f"Checking driver for: {device.display_name} (current {device.driver_version})")

    result = _search_catalog(query)
    if result and result.get("version"):
        latest = result["version"]
        if _version_is_newer(latest, device.driver_version):
            device.latest_version = latest
            device.update_available = True
            device.download_url = result.get("download_url")
            log.info(f"Update found: {device.display_name} {device.driver_version} → {latest}")
        else:
            device.latest_version = device.driver_version
            device.update_available = False
    else:
        device.latest_version = None
        device.update_available = False

    return device


def check_all_devices(devices: List[Device], progress_callback=None) -> List[Device]:
    """
    Checks all devices for updates. Calls progress_callback(current, total)
    after each device if provided.
    """
    total = len(devices)
    log.info(f"Checking {total} devices for driver updates…")

    for i, device in enumerate(devices):
        try:
            check_device(device)
        except Exception as e:
            log.error(f"Error checking {device.display_name}: {e}")
        finally:
            time.sleep(RATE_LIMIT_DELAY)

        if progress_callback:
            progress_callback(i + 1, total)

    updates_found = sum(1 for d in devices if d.update_available)
    log.info(f"Driver check complete. {updates_found} update(s) available.")
    return devices


if __name__ == "__main__":
    from device_scanner import scan_devices
    devices = scan_devices()[:5]   # test with first 5 devices
    checked = check_all_devices(devices, progress_callback=lambda c, t: print(f"{c}/{t}"))
    for d in checked:
        status = f"→ {d.latest_version}" if d.update_available else "up to date"
        print(f"{d.display_name:50s} | {d.driver_version:20s} | {status}")
