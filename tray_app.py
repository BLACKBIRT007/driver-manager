"""
tray_app.py - System tray icon using pystray + Pillow.
Lives in the background, shows notifications, opens the main window.
"""

from __future__ import annotations
import threading
from typing import Callable, Optional
from PIL import Image, ImageDraw
import pystray
from logger import log


def _create_icon_image(color: str = "#2196F3", size: int = 64) -> Image.Image:
    """Creates a simple gear-like icon for the tray."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer circle
    margin = 4
    draw.ellipse([margin, margin, size - margin, size - margin], fill=color)

    # Inner circle (hole)
    inner = size // 4
    cx = size // 2
    draw.ellipse([cx - inner, cx - inner, cx + inner, cx + inner], fill=(30, 30, 30, 255))

    # Small notch at top to suggest a gear tooth
    draw.rectangle([cx - 4, margin, cx + 4, margin + 10], fill=color)

    return img


class TrayApp:
    def __init__(
        self,
        on_open: Optional[Callable] = None,
        on_check_now: Optional[Callable] = None,
        on_quit: Optional[Callable] = None,
    ):
        self.on_open = on_open or (lambda: None)
        self.on_check_now = on_check_now or (lambda: None)
        self.on_quit = on_quit or (lambda: None)

        self._icon: Optional[pystray.Icon] = None
        self._update_count = 0

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem("Open Driver Manager", self._open, default=True),
            pystray.MenuItem("Check for Updates Now", self._check_now),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._quit),
        )

    def _open(self, icon=None, item=None):
        log.debug("Tray: Open clicked.")
        threading.Thread(target=self.on_open, daemon=True).start()

    def _check_now(self, icon=None, item=None):
        log.debug("Tray: Check Now clicked.")
        threading.Thread(target=self.on_check_now, daemon=True).start()

    def _quit(self, icon=None, item=None):
        log.info("Tray: Quit requested.")
        if self._icon:
            self._icon.stop()
        self.on_quit()

    def notify(self, title: str, message: str):
        """Shows a Windows tray notification balloon."""
        if self._icon:
            self._icon.notify(message, title)

    def set_update_badge(self, count: int):
        """Changes the icon colour to indicate pending updates."""
        self._update_count = count
        if self._icon:
            color = "#F44336" if count > 0 else "#2196F3"
            self._icon.icon = _create_icon_image(color)
            self._icon.title = (
                f"Driver Manager — {count} update(s) available"
                if count > 0
                else "Driver Manager — Up to date"
            )

    def run(self):
        """Blocking call — runs the tray icon event loop."""
        icon_image = _create_icon_image()
        self._icon = pystray.Icon(
            name="DriverManager",
            icon=icon_image,
            title="Driver Manager",
            menu=self._build_menu(),
        )
        log.info("Tray icon running.")
        self._icon.run()

    def run_detached(self):
        """Runs the tray in a background daemon thread (use when main thread owns the Qt loop)."""
        t = threading.Thread(target=self.run, daemon=True, name="TrayThread")
        t.start()
        return t
