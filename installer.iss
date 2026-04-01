[Setup]
AppName=InstaRec
AppVersion=0.4.0
AppPublisher=Sora
AppPublisherURL=https://github.com/Sora-bluesky/InstaRec
DefaultDirName={autopf}\InstaRec
DefaultGroupName=InstaRec
UninstallDisplayIcon={app}\icon.ico
OutputDir=installer_output
OutputBaseFilename=InstaRec-Setup
Compression=lzma2
SolidCompression=yes
SetupIconFile=icon.ico
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
PrivilegesRequired=lowest
CloseApplications=force
CloseApplicationsFilter=InstaRec.exe

[Files]
Source: "dist\InstaRec\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\InstaRec"; Filename: "{app}\InstaRec.exe"; IconFilename: "{app}\icon.ico"
Name: "{group}\Uninstall InstaRec"; Filename: "{uninstallexe}"
Name: "{autodesktop}\InstaRec"; Filename: "{app}\InstaRec.exe"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional options:"

[Run]
Filename: "ie4uinit.exe"; Parameters: "-show"; Flags: runhidden nowait; StatusMsg: "Refreshing icons..."
Filename: "{app}\InstaRec.exe"; Description: "Launch InstaRec"; Flags: nowait postinstall skipifsilent
