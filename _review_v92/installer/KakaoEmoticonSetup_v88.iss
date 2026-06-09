; Kakao Emoticon Profit System v90 - Inno Setup installer script
; v90 connects rejection/capture feedback to actual regenerated static/animated set outputs.
#define MyAppName "Kakao Emoticon Profit System"
#define MyAppVersion "90.0.0"
#define MyAppPublisher "Local PC Package"
#define MyAppDir "KakaoEmoticonProfitSystemV90"

[Setup]
AppId={{F86D6F6B-6612-4AF2-B080-98B9B4FCB086}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\{#MyAppDir}
DefaultGroupName={#MyAppName} v90
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=KakaoEmoticonSetup_v90
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
SetupLogging=yes
UninstallDisplayName={#MyAppName} v90

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcuts"; GroupDescription: "Shortcuts:"; Flags: checkedonce
Name: "cleanupold"; Description: "Run safe old-version cleanup preview after install"; GroupDescription: "Maintenance:"; Flags: checkedonce

[Files]
Source: "..\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "installer\*,*.zip,*.sha256.txt,.venv\*,__pycache__\*,outputs\*"

[Icons]
Name: "{autoprograms}\{#MyAppName} v90\Start Program"; Filename: "{cmd}"; Parameters: "/C ""{app}\00_STEP_3_START_PROGRAM.bat"""; WorkingDir: "{app}"
Name: "{autoprograms}\{#MyAppName} v90\Diagnostics"; Filename: "{cmd}"; Parameters: "/C ""{app}\_advanced_tools\advanced_bat\6_RUN_DIAGNOSTICS.bat"""; WorkingDir: "{app}"
Name: "{autoprograms}\{#MyAppName} v90\Clean Old Versions"; Filename: "{cmd}"; Parameters: "/C ""{app}\00_STEP_4_SAFE_CLEAN_OLD_VERSIONS.bat"""; WorkingDir: "{app}"
Name: "{autoprograms}\{#MyAppName} v90\Open Outputs"; Filename: "{cmd}"; Parameters: "/C ""{app}\_advanced_tools\advanced_bat\5_OPEN_OUTPUTS.bat"""; WorkingDir: "{app}"
Name: "{autoprograms}\{#MyAppName} v90\Uninstall"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName} v90"; Filename: "{cmd}"; Parameters: "/C ""{app}\00_STEP_3_START_PROGRAM.bat"""; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{cmd}"; Parameters: "/C ""{app}\_advanced_tools\advanced_bat\run_cleanup_old_versions_v90_preview_only.bat"""; WorkingDir: "{app}"; Flags: waituntilterminated; Tasks: cleanupold
Filename: "{cmd}"; Parameters: "/C ""{app}\4_REPAIR_ENVIRONMENT.bat"""; WorkingDir: "{app}"; Description: "Prepare Python environment"; Flags: postinstall skipifsilent unchecked waituntilterminated
Filename: "{cmd}"; Parameters: "/C ""{app}\00_STEP_3_START_PROGRAM.bat"""; WorkingDir: "{app}"; Description: "Run Kakao Emoticon Profit System v90"; Flags: postinstall skipifsilent unchecked nowait