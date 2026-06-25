#define MyAppName "StarRailAssistant"
#define MyAppVersion "unknown"
#define MyAppNumericVersion "0.0.0.0"
#define MyAppPublisher "Shasnow"
#define MyAppURL "https://starrailassistant.top/"
#define MyAppExeName "SRA.exe"
#define MyAppId "{{BD92BD8E-ACAC-403C-A609-DF8C3ABF8AD9}}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
VersionInfoVersion={#MyAppNumericVersion}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
Compression=lzma2/ultra
SolidCompression=yes
LicenseFile=SRA\LICENSE
InfoBeforeFile=install_info.txt
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=output\
OutputBaseFilename=StarRailAssistant_{#MyAppVersion}_Setup
SetupIconFile=SRAicon.ico
WizardSmallImageFile=SRAbmp.bmp
WizardStyle=modern
CloseApplications=yes
CloseApplicationsFilter=*.exe
RestartApplications=no
SetupLogging=yes
AppMutex=SRASetupMutex

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "addtopath"; Description: "Add to PATH (global access via SRA.exe)"; GroupDescription: "Environment:"; Flags: unchecked

[Files]
Source: "SRA\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Source: "SRA\cv2\*"; DestDir: "{app}\cv2"; Flags: ignoreversion nocompression recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent runascurrentuser

[Code]
const
  WM_SETTINGCHANGE = $001A;
  HWND_BROADCAST = $FFFF;

procedure BroadcastEnvironmentChange;
begin
  SendMessage(HWND_BROADCAST, WM_SETTINGCHANGE, 0,
    CastIntegerToLParam(CreateMsgRecipientParam('Environment')));
end;

procedure AddToPath(PathToAdd: string);
var
  OldPath, NewPath: string;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE,
    'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
    'Path', OldPath) then
  begin
    OldPath := '';
  end;

  if Pos(';' + UpperCase(PathToAdd) + ';', ';' + UpperCase(OldPath) + ';') > 0 then
    Exit;

  if OldPath <> '' then
    NewPath := OldPath + ';' + PathToAdd
  else
    NewPath := PathToAdd;

  RegWriteStringValue(HKEY_LOCAL_MACHINE,
    'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
    'Path', NewPath);

  BroadcastEnvironmentChange;
end;

procedure RemoveFromPath(PathToRemove: string);
var
  OldPath, NewPath: string;
  P: Integer;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE,
    'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
    'Path', OldPath) then
    Exit;

  P := Pos(';' + UpperCase(PathToRemove) + ';', ';' + UpperCase(OldPath) + ';');
  if P = 0 then
    Exit;

  NewPath := Copy(OldPath, 1, P - 1) + Copy(OldPath, P + Length(PathToRemove) + 1, MaxInt);
  if (Length(NewPath) > 0) and (NewPath[1] = ';') then
    Delete(NewPath, 1, 1);

  RegWriteStringValue(HKEY_LOCAL_MACHINE,
    'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
    'Path', NewPath);

  BroadcastEnvironmentChange;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and IsTaskSelected('addtopath') then
    AddToPath(ExpandConstant('{app}'));
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    RemoveFromPath(ExpandConstant('{app}'));
end;

