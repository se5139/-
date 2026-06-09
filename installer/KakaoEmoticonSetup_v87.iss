; Kakao Emoticon Profit System v87 - Inno Setup installer script
; v87 connects rejection/capture feedback to actual regenerated static/animated set outputs.
#define MyAppName "Kakao Emoticon Profit System"
#define MyAppVersion "87.0.0"
#define MyAppPublisher "Local PC Package"
#define MyAppDir "KakaoEmoticonProfitSystemV87"

[Setup]
AppId={{F86D6F6B-6612-4AF2-B080-98B9B4FCB086}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\{#MyAppDir}
DefaultGroupName={#MyAppName} v87
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=KakaoEmoticonSetup_v87
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
SetupLogging=yes
UninstallDisplayName={#MyAppName} v87

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcuts"; GroupDescription: "Shortcuts:"; Flags: checkedonce
Name: "cleanupold"; Description: "Run safe old-version cleanup after install"; GroupDescription: "Maintenance:"; Flags: checkedonce

[Files]
Source: "..\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "installer\*,*.zip,*.sha256.txt,.venv\*,__pycache__\*,outputs\*"

[Icons]
Name: "{autoprograms}\{#MyAppName} v87\Start Program"; Filename: "{cmd}"; Parameters: "/C ""{app}\2_START_PROGRAM.bat"""; WorkingDir: "{app}"
Name: "{autoprograms}\{#MyAppName} v87\Diagnostics"; Filename: "{cmd}"; Parameters: "/C ""{app}\_advanced_tools\advanced_bat\6_RUN_DIAGNOSTICS.bat"""; WorkingDir: "{app}"
Name: "{autoprograms}\{#MyAppName} v87\Clean Old Versions"; Filename: "{cmd}"; Parameters: "/C ""{app}\_advanced_tools\advanced_bat\14_V86_CLEAN_OLD_VERSIONS_AND_EXTRACTED.bat"""; WorkingDir: "{app}"
Name: "{autoprograms}\{#MyAppName} v87\Open Outputs"; Filename: "{cmd}"; Parameters: "/C ""{app}\_advanced_tools\advanced_bat\5_OPEN_OUTPUTS.bat"""; WorkingDir: "{app}"
Name: "{autoprograms}\{#MyAppName} v87\Uninstall"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName} v87"; Filename: "{cmd}"; Parameters: "/C ""{app}\2_START_PROGRAM.bat"""; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{cmd}"; Parameters: "/C ""{app}\_advanced_tools\advanced_bat\run_cleanup_old_versions_v86.bat"""; WorkingDir: "{app}"; Flags: waituntilterminated; Tasks: cleanupold
Filename: "{cmd}"; Parameters: "/C ""{app}\4_REPAIR_ENVIRONMENT.bat"""; WorkingDir: "{app}"; Description: "Prepare Python environment"; Flags: postinstall skipifsilent unchecked waituntilterminated
Filename: "{cmd}"; Parameters: "/C ""{app}\2_START_PROGRAM.bat"""; WorkingDir: "{app}"; Description: "Run Kakao Emoticon Profit System v87"; Flags: postinstall skipifsilent unchecked nowait