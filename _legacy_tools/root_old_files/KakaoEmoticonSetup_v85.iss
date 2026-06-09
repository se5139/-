; Kakao Emoticon Profit System v85 - Inno Setup installer script
; v85 connects rejection/capture feedback to actual regenerated static/animated set outputs.
#define MyAppName "Kakao Emoticon Profit System"
#define MyAppVersion "85.0.0"
#define MyAppPublisher "Local PC Package"
#define MyAppDir "KakaoEmoticonProfitSystemV85"

[Setup]
AppId={{F85D6F6B-6612-4AF2-B080-98B9B4FCB085}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\{#MyAppDir}
DefaultGroupName={#MyAppName} v85
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=KakaoEmoticonSetup_v85
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
SetupLogging=yes
UninstallDisplayName={#MyAppName} v85

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcuts"; GroupDescription: "Shortcuts:"; Flags: checkedonce
Name: "cleanupold"; Description: "Run safe old-version cleanup after install"; GroupDescription: "Maintenance:"; Flags: checkedonce

[Files]
Source: "..\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "installer\*,*.zip,*.sha256.txt,.venv\*,__pycache__\*,outputs\*"

[Icons]
Name: "{autoprograms}\{#MyAppName} v85\Start Program"; Filename: "{cmd}"; Parameters: "/C ""{app}\2_START_PROGRAM.bat"""; WorkingDir: "{app}"
Name: "{autoprograms}\{#MyAppName} v85\Diagnostics"; Filename: "{cmd}"; Parameters: "/C ""{app}\6_RUN_DIAGNOSTICS.bat"""; WorkingDir: "{app}"
Name: "{autoprograms}\{#MyAppName} v85\Clean Old Versions"; Filename: "{cmd}"; Parameters: "/C ""{app}\14_V85_CLEAN_OLD_VERSIONS_AND_EXTRACTED.bat"""; WorkingDir: "{app}"
Name: "{autoprograms}\{#MyAppName} v85\Open Outputs"; Filename: "{cmd}"; Parameters: "/C ""{app}\5_OPEN_OUTPUTS.bat"""; WorkingDir: "{app}"
Name: "{autoprograms}\{#MyAppName} v85\Uninstall"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName} v85"; Filename: "{cmd}"; Parameters: "/C ""{app}\2_START_PROGRAM.bat"""; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{autodesktop}\{#MyAppName} v85 - Diagnostics"; Filename: "{cmd}"; Parameters: "/C ""{app}\6_RUN_DIAGNOSTICS.bat"""; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{autodesktop}\{#MyAppName} v85 - Clean Old Versions"; Filename: "{cmd}"; Parameters: "/C ""{app}\14_V85_CLEAN_OLD_VERSIONS_AND_EXTRACTED.bat"""; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{autodesktop}\{#MyAppName} v85 - Outputs"; Filename: "{cmd}"; Parameters: "/C ""{app}\5_OPEN_OUTPUTS.bat"""; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{cmd}"; Parameters: "/C ""{app}\run_cleanup_old_versions_v85.bat"""; WorkingDir: "{app}"; Flags: waituntilterminated; Tasks: cleanupold
Filename: "{cmd}"; Parameters: "/C ""{app}\4_REPAIR_ENVIRONMENT.bat"""; WorkingDir: "{app}"; Description: "Prepare Python environment"; Flags: postinstall skipifsilent unchecked waituntilterminated
Filename: "{cmd}"; Parameters: "/C ""{app}\2_START_PROGRAM.bat"""; WorkingDir: "{app}"; Description: "Run Kakao Emoticon Profit System v85"; Flags: postinstall skipifsilent unchecked nowait