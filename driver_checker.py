"""
driver_checker.py - Checks Microsoft Update Catalog for possible newer drivers.

This is still experimental. Driver matching must be reviewed manually.
"""

from __future__ import annotations

import html
import json
import re
import time
from typing import List, Optional, Tuple

import requests

from device_scanner import Device
from logger import log

CATALOG_SEARCH_URL = "https://www.catalog.update.microsoft.com/Search.aspx"
CATALOG_DOWNLOAD_URL = "https://www.catalog.update.microsoft.com/DownloadDialog.aspx"
REQUEST_TIMEOUT = 20
RATE_LIMIT_DELAY = 0.35


def _parse_version(version_str: str) -> Tuple[int, ...]:
    if not version_str:
        return (0,)

    parts = re.split(r"[.\-,_ ]", version_str.strip())
    result = []

    for part in parts:
        try:
            result.append(int(part))
        except ValueError:
            pass

    return tuple(result) if result else (0,)


def _version_is_newer(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )
    return s


def _extract_update_ids(text: str) -> list[str]:
    ids = re.findall(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        text,
    )

    seen = set()
    out = []

    for item in ids:
        item = item.lower()

        if item not in seen:
            seen.add(item)
            out.append(item)

    return out


def _extract_versions(text: str) -> list[str]:
    versions = re.findall(r"\b\d+\.\d+(?:\.\d+){0,4}\b", text)
    return sorted(set(versions), key=_parse_version, reverse=True)


def _get_direct_download_url(session: requests.Session, update_id: str) -> Optional[str]:
    try:
        payload = {
            "updateIDs": json.dumps(
                [
                    {
                        "size": 0,
                        "languages": "",
                        "uidInfo": update_id,
                        "updateID": update_id,
                    }
                ]
            )
        }

        resp = session.post(CATALOG_DOWNLOAD_URL, data=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        text = html.unescape(resp.text)
        text = text.replace("\\/", "/").replace("\\u0026", "&")

        urls = re.findall(
            r"https?://download\.windowsupdate\.com/[^\"'<>\\\s]+",
            text,
            flags=re.IGNORECASE,
        )

        for url in urls:
            lower = url.lower()

            if any(ext in lower for ext in (".cab", ".msu", ".zip", ".exe", ".msi")):
                return url

        return urls[0] if urls else None

    except Exception as e:
        log.debug(f"Could not get direct Catalog download URL for {update_id}: {e}")
        return None


def _search_catalog(query: str) -> Optional[dict]:
    try:
        session = _session()

        resp = session.get(
            CATALOG_SEARCH_URL,
            params={"q": query},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()

        versions = _extract_versions(resp.text)
        update_ids = _extract_update_ids(resp.text)

        if not versions and not update_ids:
            return None

        best_version = versions[0] if versions else None
        download_url = None

        for update_id in update_ids[:8]:
            download_url = _get_direct_download_url(session, update_id)

            if download_url:
                break

        return {
            "version": best_version,
            "download_url": download_url,
        }

    except requests.RequestException as e:
        log.debug(f"Catalog request failed for '{query}': {e}")
        return None


def check_device(device: Device) -> Device:
    if not device.driver_version:
        return device

    query_parts = []

    if device.manufacturer and device.manufacturer.lower() not in ("microsoft", "(standard", ""):
        query_parts.append(device.manufacturer)

    query_parts.append(device.display_name)
    query_parts.append("driver")

    query = " ".join(query_parts)

    log.debug(f"Checking driver for: {device.display_name} current={device.driver_version}")

    result = _search_catalog(query)

    if result and result.get("version"):
        latest = result["version"]

        if _version_is_newer(latest, device.driver_version):
            device.latest_version = latest
            device.update_available = True
            device.download_url = result.get("download_url")
            log.info(f"Possible update found: {device.display_name} {device.driver_version} -> {latest}")
        else:
            device.latest_version = device.driver_version
            device.update_available = False
    else:
        device.latest_version = None
        device.update_available = False

    return device


def check_all_devices(devices: List[Device], progress_callback=None) -> List[Device]:
    total = len(devices)
    log.info(f"Checking {total} devices for driver updates.")

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
    log.info(f"Driver check complete. {updates_found} possible update(s) available.")

    return devices


if __name__ == "__main__":
    from device_scanner import scan_devices

    devices = scan_devices()
    checked = check_all_devices(devices, progress_callback=lambda c, t: print(f"{c}/{t}"))

    for d in checked:
        status = f"-> {d.latest_version}" if d.update_available else "up to date"
        print(f"{d.display_name:70s} | {d.driver_version:20s} | {status}")