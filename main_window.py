"""
main_window.py - Main PyQt6 UI window for Driver Update Manager.
Run this file directly during development.
"""

from __future__ import annotations
import sys
import threading
from typing import List, Optional
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QColor, QFont, QIcon, QPalette
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QHBoxLayout, QHeaderView, QLabel,
    QMainWindow, QMessageBox, QProgressBar, QPushButton, QSizePolicy,
    QStatusBar, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget, QComboBox, QGroupBox, QScrollArea, QTextEdit, QSpinBox,
    QFrame,
)

from config import config, LOG_FILE
from logger import log
from device_scanner import Device, scan_devices
from driver_checker import check_all_devices
from driver_installer import install_devices_threaded, InstallResult
from scheduler import register_startup, unregister_startup, is_registered_at_startup, run_background_scan
from tray_app import TrayApp


# ── Dark palette ──────────────────────────────────────────────────────────────

def apply_dark_palette(app: QApplication):
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#1e1e2e"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#cdd6f4"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#181825"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1e1e2e"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#cdd6f4"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#313244"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#cdd6f4"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#89b4fa"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#1e1e2e"))
    palette.setColor(QPalette.ColorRole.Link, QColor("#89b4fa"))
    app.setPalette(palette)
    app.setStyleSheet("""
        QWidget { font-family: 'Segoe UI', sans-serif; font-size: 13px; }
        QPushButton {
            background: #313244; border: 1px solid #45475a;
            border-radius: 6px; padding: 6px 16px; color: #cdd6f4;
        }
        QPushButton:hover { background: #45475a; }
        QPushButton:pressed { background: #89b4fa; color: #1e1e2e; }
        QPushButton:disabled { color: #585b70; border-color: #313244; }
        QPushButton#primary {
            background: #89b4fa; color: #1e1e2e; border: none; font-weight: 600;
        }
        QPushButton#primary:hover { background: #b4d0fe; }
        QPushButton#danger { background: #f38ba8; color: #1e1e2e; border: none; }
        QPushButton#danger:hover { background: #f5a9b8; }
        QTableWidget {
            background: #181825; border: 1px solid #313244;
            gridline-color: #313244; border-radius: 6px;
        }
        QTableWidget::item { padding: 6px; }
        QTableWidget::item:selected { background: #313244; }
        QHeaderView::section {
            background: #1e1e2e; color: #a6adc8;
            padding: 8px; border: none; border-bottom: 1px solid #313244;
            font-weight: 600;
        }
        QProgressBar {
            background: #313244; border: none; border-radius: 4px; height: 8px;
        }
        QProgressBar::chunk { background: #89b4fa; border-radius: 4px; }
        QTabWidget::pane { border: 1px solid #313244; border-radius: 6px; }
        QTabBar::tab {
            background: #1e1e2e; color: #a6adc8;
            padding: 8px 20px; border: none;
        }
        QTabBar::tab:selected { color: #89b4fa; border-bottom: 2px solid #89b4fa; }
        QGroupBox {
            border: 1px solid #313244; border-radius: 6px;
            margin-top: 12px; padding: 12px;
        }
        QGroupBox::title { color: #a6adc8; subcontrol-origin: margin; left: 10px; }
        QTextEdit {
            background: #181825; border: 1px solid #313244;
            border-radius: 6px; color: #cdd6f4; font-family: 'Consolas', monospace;
        }
        QComboBox {
            background: #313244; border: 1px solid #45475a;
            border-radius: 6px; padding: 4px 10px; color: #cdd6f4;
        }
        QScrollBar:vertical { background: #1e1e2e; width: 8px; }
        QScrollBar::handle:vertical { background: #45475a; border-radius: 4px; }
        QLabel#title { font-size: 20px; font-weight: 700; color: #cdd6f4; }
        QLabel#subtitle { color: #a6adc8; font-size: 12px; }
        QLabel#badge_green { color: #a6e3a1; font-weight: 600; }
        QLabel#badge_yellow { color: #f9e2af; font-weight: 600; }
        QLabel#badge_red { color: #f38ba8; font-weight: 600; }
    """)


# ── Worker threads ────────────────────────────────────────────────────────────

class ScanWorker(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.devices: List[Device] = []

    def run(self):
        excluded = config.get("excluded_devices", [])
        self.devices = scan_devices(exclude_ids=excluded)
        self.progress.emit(0, len(self.devices))
        self.devices = check_all_devices(self.devices, progress_callback=self.progress.emit)
        self.finished.emit(self.devices)


class InstallWorker(QThread):
    status = pyqtSignal(str, int, int)
    result = pyqtSignal(object)
    finished = pyqtSignal()

    def __init__(self, devices: List[Device], parent=None):
        super().__init__(parent)
        self.devices = devices

    def run(self):
        results = []
        total = len(self.devices)
        for i, device in enumerate(self.devices):
            self.status.emit(f"Installing {device.display_name}…", i, total)
            from driver_installer import install_device_driver
            r = install_device_driver(device)
            results.append(r)
            self.result.emit(r)
        self.status.emit("Done.", total, total)
        self.finished.emit()


# ── Devices tab ───────────────────────────────────────────────────────────────

COLUMNS = ["", "Device", "Manufacturer", "Current Driver", "Latest", "Status"]


class DevicesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.devices: List[Device] = []
        self._scan_worker: Optional[ScanWorker] = None
        self._install_worker: Optional[InstallWorker] = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Top bar
        top = QHBoxLayout()
        self.lbl_summary = QLabel("Click 'Scan' to detect your devices.")
        self.lbl_summary.setObjectName("subtitle")
        top.addWidget(self.lbl_summary)
        top.addStretch()

        self.btn_scan = QPushButton("🔍  Scan Devices")
        self.btn_scan.setObjectName("primary")
        self.btn_scan.clicked.connect(self.start_scan)
        top.addWidget(self.btn_scan)

        self.btn_update_selected = QPushButton("⬆  Update Selected")
        self.btn_update_selected.setEnabled(False)
        self.btn_update_selected.clicked.connect(self.install_selected)
        top.addWidget(self.btn_update_selected)

        self.btn_update_all = QPushButton("⬆  Update All")
        self.btn_update_all.setEnabled(False)
        self.btn_update_all.clicked.connect(self.install_all)
        top.addWidget(self.btn_update_all)

        layout.addLayout(top)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Status label
        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("subtitle")
        self.lbl_status.setVisible(False)
        layout.addWidget(self.lbl_status)

        # Table
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(0, 36)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def start_scan(self):
        self.btn_scan.setEnabled(False)
        self.btn_update_selected.setEnabled(False)
        self.btn_update_all.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.lbl_status.setText("Scanning devices…")
        self.lbl_status.setVisible(True)
        self.table.setRowCount(0)

        self._scan_worker = ScanWorker(self)
        self._scan_worker.progress.connect(self._on_scan_progress)
        self._scan_worker.finished.connect(self._on_scan_done)
        self._scan_worker.start()

    def _on_scan_progress(self, current: int, total: int):
        if total:
            self.progress.setRange(0, total)
            self.progress.setValue(current)
            self.lbl_status.setText(f"Checking drivers… {current}/{total}")

    def _on_scan_done(self, devices: List[Device]):
        self.devices = devices
        self._populate_table(devices)
        updates = sum(1 for d in devices if d.update_available)
        self.lbl_summary.setText(
            f"{len(devices)} devices found — {updates} update(s) available."
        )
        self.progress.setVisible(False)
        self.lbl_status.setVisible(False)
        self.btn_scan.setEnabled(True)
        self.btn_update_all.setEnabled(updates > 0)
        self.btn_update_selected.setEnabled(updates > 0)
        log.info(f"UI scan complete: {len(devices)} devices, {updates} updates.")

    def _populate_table(self, devices: List[Device]):
        self.table.setRowCount(0)
        for device in devices:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Checkbox
            chk = QCheckBox()
            chk.setChecked(device.update_available)
            chk.setEnabled(device.update_available)
            chk.stateChanged.connect(lambda state, d=device: setattr(d, "selected", state == Qt.CheckState.Checked.value))
            device.selected = device.update_available
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.addWidget(chk)
            cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 0, cell_widget)

            self.table.setItem(row, 1, QTableWidgetItem(device.display_name))
            self.table.setItem(row, 2, QTableWidgetItem(device.manufacturer or "—"))
            self.table.setItem(row, 3, QTableWidgetItem(device.driver_version or "—"))
            self.table.setItem(row, 4, QTableWidgetItem(device.latest_version or "—"))

            # Status badge
            if device.update_available:
                badge = QLabel("⬆ Update Available")
                badge.setObjectName("badge_yellow")
            else:
                badge = QLabel("✔ Up to date")
                badge.setObjectName("badge_green")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, 5, badge)

    def install_selected(self):
        to_install = [d for d in self.devices if d.selected and d.update_available]
        if not to_install:
            QMessageBox.information(self, "Nothing selected", "Please select at least one device to update.")
            return
        self._run_install(to_install)

    def install_all(self):
        to_install = [d for d in self.devices if d.update_available]
        self._run_install(to_install)

    def _run_install(self, devices: List[Device]):
        self.btn_scan.setEnabled(False)
        self.btn_update_selected.setEnabled(False)
        self.btn_update_all.setEnabled(False)
        self.progress.setRange(0, len(devices))
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.lbl_status.setVisible(True)

        self._install_worker = InstallWorker(devices, self)
        self._install_worker.status.connect(self._on_install_status)
        self._install_worker.result.connect(self._on_install_result)
        self._install_worker.finished.connect(self._on_install_done)
        self._install_worker.start()

    def _on_install_status(self, msg: str, current: int, total: int):
        self.lbl_status.setText(msg)
        self.progress.setValue(current)

    def _on_install_result(self, result):
        status = "✔ Installed" if result.success else "✘ Failed"
        color_name = "badge_green" if result.success else "badge_red"
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if item and item.text() == result.device.display_name:
                badge = QLabel(status)
                badge.setObjectName(color_name)
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setCellWidget(row, 5, badge)
                break

    def _on_install_done(self):
        self.btn_scan.setEnabled(True)
        self.progress.setVisible(False)
        self.lbl_status.setVisible(False)
        QMessageBox.information(self, "Done", "Driver installation complete. You may need to restart your PC.")


# ── Settings tab ──────────────────────────────────────────────────────────────

class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer = QVBoxLayout(self)
        outer.addWidget(scroll)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        scroll.setWidget(container)

        # Startup group
        grp_startup = QGroupBox("Startup")
        g1 = QVBoxLayout(grp_startup)

        self.chk_start_windows = QCheckBox("Start Driver Manager with Windows")
        self.chk_start_windows.setChecked(is_registered_at_startup())
        self.chk_start_windows.stateChanged.connect(self._toggle_startup)
        g1.addWidget(self.chk_start_windows)

        self.chk_check_startup = QCheckBox("Check for driver updates on startup")
        self.chk_check_startup.setChecked(config.get("check_on_startup", True))
        self.chk_check_startup.stateChanged.connect(lambda v: config.set("check_on_startup", bool(v)))
        g1.addWidget(self.chk_check_startup)

        layout.addWidget(grp_startup)

        # Auto-update group
        grp_auto = QGroupBox("Automatic Updates")
        g2 = QVBoxLayout(grp_auto)

        self.chk_auto_driver = QCheckBox("Automatically install driver updates (silent, background)")
        self.chk_auto_driver.setChecked(config.get("auto_update_drivers", False))
        self.chk_auto_driver.stateChanged.connect(lambda v: config.set("auto_update_drivers", bool(v)))
        g2.addWidget(self.chk_auto_driver)

        self.chk_auto_app = QCheckBox("Automatically update Driver Manager itself on startup")
        self.chk_auto_app.setChecked(config.get("auto_update_app", True))
        self.chk_auto_app.stateChanged.connect(lambda v: config.set("auto_update_app", bool(v)))
        g2.addWidget(self.chk_auto_app)

        sched_row = QHBoxLayout()
        sched_row.addWidget(QLabel("Check schedule:"))
        self.cmb_schedule = QComboBox()
        self.cmb_schedule.addItems(["On Startup", "Daily", "Weekly"])
        mapping = {"startup": 0, "daily": 1, "weekly": 2}
        self.cmb_schedule.setCurrentIndex(mapping.get(config.get("check_schedule", "daily"), 1))
        self.cmb_schedule.currentIndexChanged.connect(self._save_schedule)
        sched_row.addWidget(self.cmb_schedule)
        sched_row.addStretch()
        g2.addLayout(sched_row)

        layout.addWidget(grp_auto)

        # Notifications group
        grp_notif = QGroupBox("Notifications")
        g3 = QVBoxLayout(grp_notif)

        self.chk_notify_update = QCheckBox("Show notification when driver updates are found")
        self.chk_notify_update.setChecked(config.get("notify_on_update_found", True))
        self.chk_notify_update.stateChanged.connect(lambda v: config.set("notify_on_update_found", bool(v)))
        g3.addWidget(self.chk_notify_update)

        self.chk_notify_app = QCheckBox("Show notification after app self-update")
        self.chk_notify_app.setChecked(config.get("notify_on_app_updated", True))
        self.chk_notify_app.stateChanged.connect(lambda v: config.set("notify_on_app_updated", bool(v)))
        g3.addWidget(self.chk_notify_app)

        layout.addWidget(grp_notif)

        layout.addStretch()

    def _toggle_startup(self, state):
        if state == Qt.CheckState.Checked.value:
            ok = register_startup()
        else:
            ok = unregister_startup()
        if not ok:
            QMessageBox.warning(self, "Startup", "Could not update Windows startup setting.")

    def _save_schedule(self, idx: int):
        schedules = ["startup", "daily", "weekly"]
        config.set("check_schedule", schedules[idx])


# ── Log tab ───────────────────────────────────────────────────────────────────

class LogTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        row = QHBoxLayout()
        row.addStretch()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.load_log)
        row.addWidget(btn_refresh)
        layout.addLayout(row)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)
        self.load_log()

    def load_log(self):
        try:
            content = LOG_FILE.read_text(encoding="utf-8", errors="replace")
            # Show last 200 lines
            lines = content.splitlines()
            self.text.setPlainText("\n".join(lines[-200:]))
            # Scroll to bottom
            self.text.verticalScrollBar().setValue(self.text.verticalScrollBar().maximum())
        except OSError:
            self.text.setPlainText("No log file found yet.")


# ── Main window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, tray: Optional[TrayApp] = None):
        super().__init__()
        self.tray = tray
        self.setWindowTitle("Driver Update Manager")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)
        self._build_ui()
        self._setup_tray()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header banner
        header = QWidget()
        header.setStyleSheet("background: #181825; border-bottom: 1px solid #313244;")
        header.setFixedHeight(64)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel("🔧 Driver Update Manager")
        title.setObjectName("title")
        h_layout.addWidget(title)
        h_layout.addStretch()

        version = config.get_current_app_version()
        lbl_ver = QLabel(f"v{version}")
        lbl_ver.setObjectName("subtitle")
        h_layout.addWidget(lbl_ver)

        root.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tab_devices = DevicesTab()
        self.tab_settings = SettingsTab()
        self.tab_log = LogTab()

        self.tabs.addTab(self.tab_devices, "  Devices  ")
        self.tabs.addTab(self.tab_settings, "  Settings  ")
        self.tabs.addTab(self.tab_log, "  Log  ")
        root.addWidget(self.tabs)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready.")

    def _setup_tray(self):
        if not self.tray:
            self.tray = TrayApp(
                on_open=self.show_window,
                on_check_now=self.tab_devices.start_scan,
                on_quit=self.quit_app,
            )
            self.tray.run_detached()

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        if config.get("minimize_to_tray", True):
            event.ignore()
            self.hide()
        else:
            event.accept()

    def quit_app(self):
        QApplication.quit()

    def notify_updates(self, updates: list):
        count = len(updates)
        if self.tray:
            self.tray.set_update_badge(count)
            if config.get("notify_on_update_found", True):
                self.tray.notify(
                    "Driver Updates Available",
                    f"{count} driver update(s) found. Click to open Driver Manager.",
                )


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    apply_dark_palette(app)

    tray = TrayApp()
    window = MainWindow(tray=tray)

    # Wire tray to window
    tray.on_open = window.show_window
    tray.on_check_now = window.tab_devices.start_scan
    tray.on_quit = window.quit_app
    tray.run_detached()

    window.show()

    # Background scan on startup
    if config.get("check_on_startup", True):
        run_background_scan(
            on_updates_found=window.notify_updates,
        )

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
