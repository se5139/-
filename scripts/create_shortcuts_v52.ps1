param(
  [string]$AppDir = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$desktop = [Environment]::GetFolderPath('DesktopDirectory')
if ([string]::IsNullOrWhiteSpace($desktop) -or -not (Test-Path $desktop)) {
  $oneDriveDesktop = Join-Path $env:USERPROFILE 'OneDrive\Desktop'
  if (Test-Path $oneDriveDesktop) { $desktop = $oneDriveDesktop }
  else { $desktop = Join-Path $env:USERPROFILE 'Desktop' }
}

$shell = New-Object -ComObject WScript.Shell
$shortcuts = @(
  @{Name='Kakao Emoticon v52'; Target='2_START_PROGRAM.bat'},
  @{Name='Kakao Emoticon v52 - Repair'; Target='4_REPAIR_ENVIRONMENT.bat'},
  @{Name='Kakao Emoticon v52 - Diagnostics'; Target='6_RUN_DIAGNOSTICS.bat'},
  @{Name='Kakao Emoticon v52 - Outputs'; Target='5_OPEN_OUTPUTS.bat'},
  @{Name='Kakao Emoticon v52 - Static To Animated Check'; Target='18_V52_API_GUARDRAIL_LEDGER_CHECK.bat'},
  @{Name='Kakao Emoticon v52 - Clean Old Versions'; Target='14_V52_CLEAN_OLD_VERSIONS.bat'}
)

foreach ($item in $shortcuts) {
  $shortcutPath = Join-Path $desktop ($item.Name + '.lnk')
  $targetPath = Join-Path $AppDir $item.Target
  if (-not (Test-Path $targetPath)) { Write-Host "Missing target: $targetPath"; continue }
  $shortcut = $shell.CreateShortcut($shortcutPath)
  $shortcut.TargetPath = $targetPath
  $shortcut.WorkingDirectory = $AppDir
  $shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,44"
  $shortcut.Save()
  Write-Host "Created shortcut: $shortcutPath"
}
Write-Host "Desktop folder: $desktop"
