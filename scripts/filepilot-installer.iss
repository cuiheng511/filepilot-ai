; FilePilot AI — Inno Setup Installer Script
; Requires Inno Setup 6+ (https://jrsoftware.org/isdl.php)
; Compile: iscc /dMyAppVersion=x.y.z scripts\filepilot-installer.iss
;
; For digital signing (optional), set env vars before running build_installer.ps1:
;   $env:SIGNTOOL_PATH = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe"
;   $env:SIGN_CERTIFICATE_SHA1 = "YOUR_CERT_SHA1_HASH"

#define MyAppName "FilePilot AI"
#ifndef MyAppVersion
  #define MyAppVersion "0.4.1"
#endif
#define MyAppPublisher "cuiheng511"
#define MyAppURL "https://github.com/cuiheng511/filepilot-ai"
#define MyAppExeName "FilePilot.exe"
#define MyAppAssocName "FilePilot Index"
#define MyAppAssocExt ".fpindex"

[Setup]
AppId={{B8F4A2D1-9C3E-4F7A-8B5D-2E1A6F9C3D7B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL=https://github.com/cuiheng511/filepilot-ai/releases
AppReadmeFile={#MyAppURL}#readme
AppContact=cuiheng511@users.noreply.github.com
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=FilePilot-AI-Setup-{#MyAppVersion}
SetupIconFile=..\filepilot\resources\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=commandline
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=no
RestartApplications=no
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName}
VersionInfoCopyright=Copyright (c) 2025 {#MyAppPublisher}
DisableStartupPrompt=yes
UsedUserAreasWarning=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checkedonce

[Files]
Source: "..\dist\FilePilot\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\FilePilot\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Registry]
; File association — .fpindex (reserved for future use)
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocExt}\OpenWithProgids"; ValueType: string; ValueName: "{#MyAppAssocName}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocName}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocName}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
; Install path + version for update checker
Root: HKCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey

[Code]
{ ── Check if app is running before install ── }
function IsFilePilotRunning(): Boolean;
var
  WMIService: Variant;
  Processes: Variant;
begin
  Result := False;
  try
    WMIService := CreateOleObject('WbemScripting.SWbemLocator');
    WMIService := WMIService.ConnectServer('.', 'root\cimv2');
    Processes := WMIService.ExecQuery('SELECT Name FROM Win32_Process WHERE Name="FilePilot.exe"');
    Result := (Processes.Count > 0);
  except
    Result := False;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Result := '';
  if IsFilePilotRunning() then
  begin
    if MsgBox('FilePilot AI is currently running.'#13#13 +
              'Do you want to close it before continuing?',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      Exec('taskkill.exe', '/IM FilePilot.exe /F', '',
           SW_HIDE, ewWaitUntilTerminated, ResultCode);
      Sleep(1000);
    end
    else
      Result := 'Please close FilePilot AI manually before continuing.';
  end;
end;
