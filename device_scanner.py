"""
device_scanner.py - Scans Windows devices via WMI and returns driver information.
Requires: wmi (pip install wmi), pywin32
"""

from __future__ import annotations
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional
from logger import log


@dataclass
class Device:
    name: str
    device_id: str
    manufacturer: str
    driver_version: str
    driver_date: str
    device_class: str
    status: str
    inf_name: str = ""
    hardware_ids: List[str] = field(default_factory=list)
    latest_version: Optional[str] = None   # filled in by driver_checker
    update_available: bool = False
    download_url: Optional[str] = None
    selected: bool = False                  # user selection in UI

    @property
    def display_name(self) -> str:
        return self.name or "Unknown Device"

    @property
    def needs_update(self) -> bool:
        return self.update_available and bool(self.latest_version)


def _get_devices_via_wmi() -> List[Device]:
    """Primary method: uses the wmi Python package."""
    import wmi
    devices: List[Device] = []
    c = wmi.WMI()

    for dev in c.Win32_PnPSignedDriver():
        try:
            name = (dev.DeviceName or "").strip()
            if not name or name.lower() in ("", "unknown"):
                continue

            device = Device(
                name=name,
                device_id=(dev.DeviceID or "").strip(),
                manufacturer=(dev.Manufacturer or "").strip(),
                driver_version=(dev.DriverVersion or "").strip(),
                driver_date=_format_wmi_date(dev.DriverDate),
                device_class=(dev.DeviceClass or "").strip(),
                status="OK",
                inf_name=(dev.InfName or "").strip(),
            )
            devices.append(device)
        except Exception as e:
            log.debug(f"Skipped device during WMI scan: {e}")

    log.info(f"WMI scan found {len(devices)} devices.")
    return devices


def _get_devices_via_powershell() -> List[Device]:
    """Fallback: queries via PowerShell when wmi package is unavailable."""
    ps_script = (
        "Get-WmiObject Win32_PnPSignedDriver | "
        "Where-Object { $_.DeviceName -ne $null -and $_.DeviceName -ne '' } | "
        "Select-Object DeviceName, DeviceID, Manufacturer, DriverVersion, DriverDate, DeviceClass, InfName | "
        "ConvertTo-Json -Depth 2"
    )
    result = subprocess.run(
        ["powershell", "-NonInteractive", "-Command", ps_script],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        log.error(f"PowerShell scan failed: {result.stderr}")
        return []

    import json
    raw = json.loads(result.stdout or "[]")
    if isinstance(raw, dict):
        raw = [raw]

    devices: List[Device] = []
    for item in raw:
        name = (item.get("DeviceName") or "").strip()
        if not name:
            continue
        devices.append(Device(
            name=name,
            device_id=(item.get("DeviceID") or "").strip(),
            manufacturer=(item.get("Manufacturer") or "").strip(),
            driver_version=(item.get("DriverVersion") or "").strip(),
            driver_date=_format_wmi_date(item.get("DriverDate")),
            device_class=(item.get("DeviceClass") or "").strip(),
            status="OK",
            inf_name=(item.get("InfName") or "").strip(),
        ))

    log.info(f"PowerShell scan found {len(devices)} devices.")
    return devices


def _format_wmi_date(raw: Optional[str]) -> str:
    """Converts WMI date string '20231015000000.000000+000' → '2023-10-15'."""
    if not raw:
        return "Unknown"
    try:
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    except Exception:
        return str(raw)


def scan_devices(exclude_ids: Optional[List[str]] = None) -> List[Device]:
    """
    Main entry point. Returns a list of Device objects for all installed hardware.
    Tries wmi package first, falls back to PowerShell.
    """
    exclude_ids = set(exclude_ids or [])
    log.info("Starting device scan…")

    try:
        import wmi  # noqa: F401
        devices = _get_devices_via_wmi()
    except ImportError:
        log.warning("wmi package not found — falling back to PowerShell.")
        devices = _get_devices_via_powershell()
    except Exception as e:
        log.error(f"WMI scan error: {e} — falling back to PowerShell.")
        devices = _get_devices_via_powershell()

    # Apply exclusions
    devices = [d for d in devices if d.device_id not in exclude_ids]

    # Sort: name alphabetically
    devices.sort(key=lambda d: d.display_name.lower())
    return devices


if __name__ == "__main__":
    devs = scan_devices()
    for d in devs:
        print(f"{d.display_name:50s} | {d.driver_version:20s} | {d.driver_date} | {d.manufacturer}")
