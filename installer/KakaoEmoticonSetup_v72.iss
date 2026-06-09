; Kakao Emoticon Profit System v72 - Inno Setup installer script
; v72 adds submission autofix and lock workflow.
#define MyAppName "Kakao Emoticon Profit System"
#define MyAppVersion "72.0.0"
#define MyAppPublisher "Local PC Package"
#define MyAppDir "KakaoEmoticonProfitSystemV72"

[Setup]
AppId={{A64B77DD-126B-45BB-A8D0-DA34D1137B64}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\{#MyAppDir}
DefaultGroupName={#MyAppName} v72
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=KakaoEmoticonSetup_v72
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
SetupLogging=yes
UninstallDisplayName={#MyAppName} v72

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcuts"; GroupDescription: "Shortcuts:"; Flags: checkedonce
Name: "cleanupold"; Description: "Run safe old-version cleanup after install"; GroupDescription: "Maintenance:"; Flags: checkedonce

[Files]
Source: "..\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "installer\*,*.zip,*.sha256.txt,.venv\*,__pycache__\*,outputs\*"

[Icons]
Name: "{autoprograms}\{#MyAppName} v72\Start Program"; Filename: "{cmd}"; Parameters: "/C ""{app}\2_START_PROGRAM.bat"""; WorkingDir: "{app}"
Name: "{autoprograms}\{#MyAppName} v72\Diagnostics"; Filename: "{cmd}"; Parameters: "/C ""{app}\6_RUN_DIAGNOSTICS.bat"""; WorkingDir: "{app}"
Name: "{autoprograms}\{#MyAppName} v72\Clean Old Versions"; Filename: "{cmd}"; Parameters: "/C ""{app}\14_V72_CLEAN_OLD_VERSIONS_AND_EXTRACTED.bat"""; WorkingDir: "{app}"
Name: "{autoprograms}\{#MyAppName} v72\Open Outputs"; Filename: "{cmd}"; Parameters: "/C ""{app}\5_OPEN_OUTPUTS.bat"""; WorkingDir: "{app}"
Name: "{autoprograms}\{#MyAppName} v72\Uninstall"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName} v72"; Filename: "{cmd}"; Parameters: "/C ""{app}\2_START_PROGRAM.bat"""; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{autodesktop}\{#MyAppName} v72 - Diagnostics"; Filename: "{cmd}"; Parameters: "/C ""{app}\6_RUN_DIAGNOSTICS.bat"""; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{autodesktop}\{#MyAppName} v72 - Clean Old Versions"; Filename: "{cmd}"; Parameters: "/C ""{app}\14_V72_CLEAN_OLD_VERSIONS_AND_EXTRACTED.bat"""; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{autodesktop}\{#MyAppName} v72 - Outputs"; Filename: "{cmd}"; Parameters: "/C ""{app}\5_OPEN_OUTPUTS.bat"""; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{cmd}"; Parameters: "/C ""{app}\run_cleanup_old_versions_v72.bat"""; WorkingDir: "{app}"; Flags: waituntilterminated; Tasks: cleanupold
Filename: "{cmd}"; Parameters: "/C ""{app}\4_REPAIR_ENVIRONMENT.bat"""; WorkingDir: "{app}"; Description: "Prepare Python environment"; Flags: postinstall skipifsilent unchecked waituntilterminated
Filename: "{cmd}"; Parameters: "/C ""{app}\2_START_PROGRAM.bat"""; WorkingDir: "{app}"; Description: "Run Kakao Emoticon Profit System v72"; Flags: postinstall skipifsilent unchecked nowait