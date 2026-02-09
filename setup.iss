; Script généré pour Inno Setup
; Téléchargez Inno Setup ici : https://jrsoftware.org/isdl.php

#define MyAppName "YouTube Downloader"
#define MyAppVersion "1.0.2"
#define MyAppPublisher "GarfieldTVA"
#define MyAppURL "https://github.com/GarfieldTVA/YoutubeDownloader-Dist"
#define MyAppExeName "YouTubeDownloader_v1.0.1.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{A3D8F9C1-4E2B-4B5A-9F8D-1C2E3F4G5H6I}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
; Uncomment the following line to run in non administrative install mode (install for current user only.)
PrivilegesRequired=lowest
OutputDir=.
OutputBaseFilename=YouTubeDownloader_Setup_v1.0.1
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; L'exécutable principal
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; FFMPEG (Nécessaire pour la fusion audio/vidéo)
; ATTENTION : Vous devez avoir ffmpeg.exe dans le même dossier que ce script !
; Source: "ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion; Check: FileExists('ffmpeg.exe')

; Deno (si vous voulez l'inclure, sinon le logiciel le télécharge)
; Source: "deno.exe"; DestDir: "{app}"; Flags: ignoreversion; Check: FileExists('deno.exe')

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
