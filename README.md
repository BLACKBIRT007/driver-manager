# Driver Update Manager

Automatically scans your PC for outdated drivers, lets you update them individually or all at once, and runs silently in the background from startup.

---

## Quick Start (Development)

1. Install Python 3.11+ from https://python.org (check "Add to PATH")
2. Double-click `install_dependencies.bat`
3. Run: `python main_window.py`

---

## Folder Structure

```
driver_manager/
├── config.py              # Settings management
├── logger.py              # Log file setup
├── device_scanner.py      # WMI device detection
├── driver_checker.py      # Checks Microsoft Update Catalog
├── driver_installer.py    # Downloads & installs drivers
├── auto_updater.py        # App self-update from GitHub
├── launcher.py            # Tiny bootstrap (runs on Windows startup)
├── scheduler.py           # Startup registration & background scans
├── main_window.py         # PyQt6 UI — run this to launch the app
├── tray_app.py            # System tray icon
├── version.txt            # Current version number (e.g. 1.0.0)
├── requirements.txt       # Python packages
├── install_dependencies.bat
├── build.bat              # Build EXEs locally
├── setup_builder/
│   └── installer.iss      # Inno Setup script
└── .github/
    └── workflows/
        └── release.yml    # Auto-build on GitHub tag push
```

---

## Step-by-Step: GitHub Setup & Publishing

### Step 1 — Create your GitHub repo

1. Go to https://github.com and sign in (or create a free account)
2. Click **New repository**
3. Name it `driver-manager`
4. Set to **Public** (required for free Certum cert)
5. Click **Create repository**

### Step 2 — Update your repo name in the code

Open `config.py` and change this line:
```python
GITHUB_REPO = "yourusername/driver-manager"
```
Replace `yourusername` with your actual GitHub username.

Also update `setup_builder/installer.iss`:
```
#define AppPublisher "YourName"
#define AppURL "https://github.com/yourusername/driver-manager"
```

### Step 3 — Push your code to GitHub

Open a terminal in your project folder and run:
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/driver-manager.git
git push -u origin main
```

### Step 4 — Make your first release

Every time you want to publish a new version:

```bash
# Update version.txt first — change "1.0.0" to whatever version you want
# Then:
git add .
git commit -m "Release v1.0.0"
git tag v1.0.0
git push && git push --tags
```

GitHub Actions will automatically:
- Build `DriverManager.exe` and `Launcher.exe`
- Create the `DriverManager_Setup_1.0.0.exe` installer
- Attach it to a GitHub Release at:
  `https://github.com/yourusername/driver-manager/releases`

### Step 5 — Create your free download website (GitHub Pages)

1. In your repo on GitHub, go to **Settings → Pages**
2. Under "Source" select **Deploy from a branch**
3. Choose **main** branch, **/ (root)** folder → Save
4. Create a file called `index.html` in your repo with a download button:

```html
<!DOCTYPE html>
<html>
<head><title>Driver Update Manager</title></head>
<body>
  <h1>Driver Update Manager</h1>
  <p>Free, open-source Windows driver updater.</p>
  <a href="https://github.com/yourusername/driver-manager/releases/latest/download/DriverManager_Setup_1.0.0.exe">
    Download Latest Version
  </a>
</body>
</html>
```

Your site will be live at: `https://yourusername.github.io/driver-manager`

---

## Certum Open Source Code Signing Certificate (FREE)

This removes the "Windows protected your PC" SmartScreen warning.

### What it does
Windows shows a scary warning for any unsigned `.exe`. A code signing
certificate tells Windows "this app comes from a verified publisher."
Certum gives these **free** to open-source developers.

### Requirements
- Your project must be open source (public GitHub repo ✓)
- You must be an individual developer (not a company)
- The certificate is valid for 1 year and renewable for free

### Step-by-Step

**1. Go to the Certum website**
Visit: https://www.certum.eu/en/cert_offer_en/open-source-code-signing/

**2. Click "Get Certificate" / "Order"**
The product is called **"Open Source Code Signing"** — price should show as €0 / free.

**3. Create an account**
Fill in your name, email, country. They'll send a verification email.

**4. Verify your identity**
Certum will ask you to verify via:
- A video call (they check your ID/passport — takes ~10 minutes)
- OR upload a scan of your government ID

**5. Download your certificate**
After approval (usually 1–3 days), you download a `.pfx` file.
This is your signing certificate — keep it private and safe.

**6. Sign your EXEs**

Install the Windows SDK (free from Microsoft), then run:
```cmd
signtool sign /fd sha256 /a ^
  /f "C:\path\to\your_certificate.pfx" /p "your_password" ^
  /tr http://timestamp.sectigo.com /td sha256 ^
  "DriverManager.exe" "Launcher.exe"
```

**7. Sign inside GitHub Actions (optional but recommended)**

Store your `.pfx` as a GitHub Secret:
- Go to your repo → Settings → Secrets → Actions → New secret
- Name: `CODE_SIGNING_CERT` — paste the base64-encoded `.pfx`:
  ```powershell
  [Convert]::ToBase64String([IO.File]::ReadAllBytes("cert.pfx")) | clip
  ```
- Name: `CODE_SIGNING_PASSWORD` — your certificate password

Then add this step to `release.yml` before the Inno Setup step:
```yaml
- name: Sign EXEs
  run: |
    $cert = [Convert]::FromBase64String("${{ secrets.CODE_SIGNING_CERT }}")
    [IO.File]::WriteAllBytes("cert.pfx", $cert)
    signtool sign /fd sha256 /f cert.pfx /p "${{ secrets.CODE_SIGNING_PASSWORD }}" `
      /tr http://timestamp.sectigo.com /td sha256 `
      release\DriverManager.exe release\Launcher.exe
  shell: pwsh
```

### What users see after signing
- **Without cert:** "Windows protected your PC" → users must click "More info" → "Run anyway"
- **With Certum cert:** No warning at all — Windows installs it like any normal program ✓

---

## Updating the App

To publish a new version:

1. Make your code changes
2. Update `version.txt` (e.g. change `1.0.0` to `1.1.0`)
3. Run:
   ```bash
   git add .
   git commit -m "v1.1.0 - describe your changes"
   git tag v1.1.0
   git push && git push --tags
   ```
4. GitHub Actions builds and publishes automatically.
5. Every user's app will silently update itself on next Windows startup. ✓
