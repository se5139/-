param(
  [string]$AppDir = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Continue'

function Add-UniquePath([System.Collections.Generic.List[string]]$List, [string]$PathText) {
  if ([string]::IsNullOrWhiteSpace($PathText)) { return }
  try { $full = [System.IO.Path]::GetFullPath($PathText).TrimEnd('\') } catch { $full = $PathText.TrimEnd('\') }
  if ((Test-Path $full) -and (-not $List.Contains($full))) { $List.Add($full) }
}

$desktopPaths = New-Object System.Collections.Generic.List[string]
Add-UniquePath $desktopPaths ([Environment]::GetFolderPath('DesktopDirectory'))
Add-UniquePath $desktopPaths (Join-Path $env:USERPROFILE 'Desktop')
Add-UniquePath $desktopPaths (Join-Path $env:USERPROFILE 'OneDrive\Desktop')

if ($desktopPaths.Count -eq 0) {
  Write-Host '[ERROR] No desktop folder found.'
  exit 1
}

$shell = New-Object -ComObject WScript.Shell
$shortcuts = @(
  @{Name='Kakao Emoticon v53'; Target='2_START_PROGRAM.bat'},
  @{Name='Kakao Emoticon v53 - Repair'; Target='4_REPAIR_ENVIRONMENT.bat'},
  @{Name='Kakao Emoticon v53 - Diagnostics'; Target='6_RUN_DIAGNOSTICS.bat'},
  @{Name='Kakao Emoticon v53 - Outputs'; Target='5_OPEN_OUTPUTS.bat'},
  @{Name='Kakao Emoticon v53 - Clean Old Versions'; Target='14_V53_CLEAN_OLD_VERSIONS_AND_EXTRACTED.bat'},
  @{Name='Kakao Emoticon v53 - Install Cleanup Check'; Target='20_V53_INSTALL_CLEANUP_SHORTCUT_CHECK.bat'}
)

$created = 0
foreach ($desktop in $desktopPaths) {
  foreach ($item in $shortcuts) {
    $targetPath = Join-Path $AppDir $item.Target
    if (-not (Test-Path $targetPath)) {
      Write-Host "[WARN] Missing target: $targetPath"
      continue
    }
    $shortcutPath = Join-Path $desktop ($item.Name + '.lnk')
    try {
      $shortcut = $shell.CreateShortcut($shortcutPath)
      $shortcut.TargetPath = $targetPath
      $shortcut.WorkingDirectory = $AppDir
      $shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,44"
      $shortcut.Description = 'Kakao Emoticon Profit System v53'
      $shortcut.Save()
      $created += 1
      Write-Host "Created shortcut: $shortcutPath"
    } catch {
      Write-Host "[WARN] Failed shortcut: $shortcutPath $($_.Exception.Message)"
    }
  }
}

Write-Host "Desktop folders used:"
foreach ($d in $desktopPaths) { Write-Host "- $d" }
Write-Host "Created shortcut count: $created"
if ($created -lt 1) { exit 1 }
exit 0
