[Setup]
AppId=CyberNexusHUD
AppName=CYBER NEXUS HUD
AppVersion=0.6.11
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
DefaultDirName={localappdata}\Programs\CyberNexusHUD
DefaultGroupName=CYBER NEXUS HUD
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=CyberNexusHUD-Setup-Windows
Compression=lzma2/fast
SolidCompression=yes
UninstallDisplayIcon={app}\NovaBar\HealthPerfsBar.exe

[InstallDelete]
; Remove names used by older launchers; Inno upgrades the standard same-AppId
; CyberNexusInstaller.exe in place. Do not touch user data or NovaBar runtimes.
Type: files; Name: "{app}\\NovaBarInstaller.exe"
Type: files; Name: "{app}\\CyberNexusInstaller-old.exe"

[Files]

Source: "..\dist\HealthPerfsBar\*"; DestDir: "{app}\NovaBar"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "native-install.json"; DestDir: "{app}\NovaBar"

[Icons]
Name: "{group}\NovaBar"; Filename: "{app}\NovaBar\HealthPerfsBar.exe"
Name: "{group}\Désinstaller NovaBar"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\NovaBar\HealthPerfsBar.exe"; Description: "Ouvrir NovaBar"; Flags: nowait postinstall skipifsilent
