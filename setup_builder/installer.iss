#define AppName "Driver Handler by CROD"
#define AppVersion "1.0.0"
#define AppPublisher "CROD"
#define AppURL "https://github.com/BLACKBIRT007/driver-manager"
#define AppExeName "DriverHandlerByCROD.exe"
#define LauncherExeName "Launcher.exe"

[Setup]
AppId={{C7D9A8E2-1F49-4B14-B0B9-CROD00000001}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\Driver Handler by CROD
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=Driver_Handler_By_CROD_Setup_{#AppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayName={#AppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "startup"; Description: "Start Driver Handler by CROD with Windows"; GroupDescription: "Startup options:"; Flags: checkedonce

[Files]
Source: "..\release\DriverHandlerByCROD.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\release\Launcher.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\release\version.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#LauncherExeName}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#LauncherExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "DriverHandlerByCROD"; ValueData: """{app}\{#LauncherExeName}"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\{#LauncherExeName}"; Description: "Launch Driver Handler by CROD"; Flags: nowait postinstall skipifsilent
