[Setup]
AppName=InstaRec
AppVersion=0.2.0
AppPublisher=Sora
AppPublisherURL=https://github.com/Sora-bluesky/InstaRec
DefaultDirName={autopf}\InstaRec
DefaultGroupName=InstaRec
UninstallDisplayIcon={app}\InstaRec.exe
OutputDir=dist
OutputBaseFilename=InstaRec-Setup-0.2.0
Compression=lzma2
SolidCompression=yes
SetupIconFile=icon.ico
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
PrivilegesRequired=lowest

[Files]
Source: "dist\InstaRec.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\InstaRec"; Filename: "{app}\InstaRec.exe"
Name: "{group}\Uninstall InstaRec"; Filename: "{uninstallexe}"
Name: "{autodesktop}\InstaRec"; Filename: "{app}\InstaRec.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional options:"

[Run]
Filename: "{app}\InstaRec.exe"; Description: "Launch InstaRec"; Flags: nowait postinstall skipifsilent
