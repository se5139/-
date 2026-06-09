param(
  [string]$AppDir = ''
)

$ErrorActionPreference = 'Continue'

function Clean-InputPath([string]$PathText) {
  if ([string]::IsNullOrWhiteSpace($PathText)) { return '' }
  $p = $PathText.Trim()
  $p = $p.Trim('"')
  try { $p = [System.IO.Path]::GetFullPath($p) } catch { }
  if ($p.Length -gt 3) { $p = $p.TrimEnd('\') }
  return $p
}

function Add-UniquePath([System.Collections.Generic.List[string]]$List, [string]$PathText) {
  $full = Clean-InputPath $PathText
  if ([string]::IsNullOrWhiteSpace($full)) { return }
  if ((Test-Path -LiteralPath $full) -and (-not $List.Contains($full))) { $List.Add($full) }
}

$appRoot = Clean-InputPath $AppDir
if ([string]::IsNullOrWhiteSpace($appRoot)) {
  $appRoot = Clean-InputPath (Split-Path -Parent $PSScriptRoot)
}

if (-not (Test-Path -LiteralPath $appRoot)) {
  Write-Host "[ERROR] AppDir not found: $appRoot"
  exit 1
}

$desktopPaths = New-Object System.Collections.Generic.List[string]
Add-UniquePath $desktopPaths ([Environment]::GetFolderPath('DesktopDirectory'))
Add-UniquePath $desktopPaths (Join-Path $env:USERPROFILE 'Desktop')
Add-UniquePath $desktopPaths (Join-Path $env:USERPROFILE 'OneDrive\Desktop')
Add-UniquePath $desktopPaths (Join-Path $env:USERPROFILE 'OneDrive\Desktop')
# Korean OneDrive desktop is discovered by DesktopDirectory above on Korean Windows.

if ($desktopPaths.Count -eq 0) {
  Write-Host '[ERROR] No desktop folder found.'
  exit 1
}

$shell = New-Object -ComObject WScript.Shell
$shortcuts = @(
  @{Name='Kakao Emoticon v54'; Target='2_START_PROGRAM.bat'},
  @{Name='Kakao Emoticon v54 - Repair'; Target='4_REPAIR_ENVIRONMENT.bat'},
  @{Name='Kakao Emoticon v54 - Diagnostics'; Target='6_RUN_DIAGNOSTICS.bat'},
  @{Name='Kakao Emoticon v54 - Outputs'; Target='5_OPEN_OUTPUTS.bat'},
  @{Name='Kakao Emoticon v54 - Clean Old Versions'; Target='14_V54_CLEAN_OLD_VERSIONS_AND_EXTRACTED.bat'},
  @{Name='Kakao Emoticon v54 - Installer Check'; Target='21_V54_INSTALLER_HOTFIX_CHECK.bat'}
)

$created = 0
foreach ($desktop in $desktopPaths) {
  foreach ($item in $shortcuts) {
    $targetPath = Join-Path $appRoot $item.Target
    if (-not (Test-Path -LiteralPath $targetPath)) {
      Write-Host "[WARN] Missing target: $targetPath"
      continue
    }
    $shortcutPath = Join-Path $desktop ($item.Name + '.lnk')
    try {
      $shortcut = $shell.CreateShortcut($shortcutPath)
      $shortcut.TargetPath = $targetPath
      $shortcut.WorkingDirectory = $appRoot
      $shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,44"
      $shortcut.Description = 'Kakao Emoticon Profit System v54'
      $shortcut.Save()
      $created += 1
      Write-Host "Created shortcut: $shortcutPath"
    } catch {
      Write-Host "[WARN] Failed shortcut: $shortcutPath $($_.Exception.Message)"
    }
  }
}

Write-Host 'Desktop folders used:'
foreach ($d in $desktopPaths) { Write-Host "- $d" }
Write-Host "Created shortcut count: $created"
if ($created -lt 1) { exit 1 }
exit 0
