# Driver Handler by CROD

> **AI-assisted Windows driver manager.**  
> Scan installed devices, review possible driver updates, and keep the app itself updated through GitHub Releases.

---

## What this is

Driver Handler by CROD is a Windows desktop app made in Python.

It is designed to:

- scan installed hardware devices
- read current driver versions
- check for possible newer driver versions
- let the user update selected drivers
- run from the Windows tray
- start with Windows
- self-update from GitHub Releases
- publish installers through GitHub Actions
- provide a GitHub Pages download site

The app is not pretending to be magic. Driver updates are risky, so automatic driver installs are disabled by default.

---

## AI-built, openly

This project was heavily built, debugged, renamed, and reorganised with AI assistance.

AI helped with:

- architecture
- file layout
- PyInstaller builds
- launcher/core split
- GitHub Actions release workflow
- Inno Setup packaging
- GitHub Pages download links
- README structure
- troubleshooting failed builds and bad release paths

The final result is still human-owned code. AI helped build the structure, but every driver install should still be reviewed carefully.

---

## Final app structure

Installed folder:

```text
Driver Handler by CROD/
â”œâ”€ DriverHandlerByCROD.exe
â”œâ”€ DriverHandlerByCROD_Core.exe
â””â”€ version.txt

Built by C.R.O.D. Co-developed with AI.