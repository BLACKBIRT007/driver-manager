; Driver Update Manager - Inno Setup Script
; Download Inno Setup free from: https://jrsoftware.org/isdl.php

#define AppName "Driver Update Manager"
#define AppVersion "1.0.0"
#define AppPublisher "YourName"
#define AppURL "https://github.com/yourusername/driver-manager"
#define AppExeName "DriverManager.exe"
#define LauncherExeName "Launcher.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=installer_output
OutputBaseFilename=DriverManager_Setup_{#AppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#AppExeName}

; Uncomment and fill in if you have a code signing certificate:
; SignTool=mysigntool sign /fd sha256 /a /tr http://timestamp.sectigo.com /td sha256 $f

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startupentry"; Description: "Start Driver Manager with Windows"; GroupDescription: "Startup:"; Flags: checked

[Files]
; Main app
Source: "..\release\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Launcher (what Windows startup actually runs)
Source: "..\release\{#LauncherExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Version file (read by auto_updater)
Source: "..\version.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Registry]
; Windows startup (Launcher, not the main app)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ^
    ValueType: string; ValueName: "DriverUpdateManager"; ^
    ValueData: """{app}\{#LauncherExeName}"""; ^
    Flags: uninsdeletevalue; Tasks: startupentry

[Run]
; Launch the main app after install finishes
Filename: "{app}\{#AppExeName}"; ^
    Description: "Launch Driver Update Manager"; ^
    Flags: nowait postinstall skipifsilent

[UninstallRun]
; Remove startup entry on uninstall
Filename: "reg"; Parameters: "delete ""HKCU\Software\Microsoft\Windows\CurrentVersion\Run"" /v DriverUpdateManager /f"; Flags: runhidden

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Nothing extra needed — registry key handles startup
  end;
end;
