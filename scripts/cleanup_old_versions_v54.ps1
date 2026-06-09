param(
  [int]$CurrentVersion = 54,
  [ValidateSet('ReportOnly','AutoConfirm')]
  [string]$Mode = 'ReportOnly',
  [string]$ProtectSource = '',
  [string]$ProtectTarget = ''
)

$ErrorActionPreference = 'Continue'
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$localAppData = $env:LOCALAPPDATA
if ([string]::IsNullOrWhiteSpace($localAppData) -or -not (Test-Path -LiteralPath $localAppData)) {
  Write-Host '[ERROR] LOCALAPPDATA not found.'
  exit 1
}

function Clean-InputPath([string]$PathText) {
  if ([string]::IsNullOrWhiteSpace($PathText)) { return '' }
  $p = $PathText.Trim()
  $p = $p.Trim('"')
  try { $p = [System.IO.Path]::GetFullPath($p) } catch { }
  if ($p.Length -gt 3) { $p = $p.TrimEnd('\') }
  return $p
}

function Is-ProtectedPath([string]$Candidate) {
  $c = Clean-InputPath $Candidate
  foreach ($p in @($script:protectSourceNorm, $script:protectTargetNorm, $script:backupRootNorm)) {
    if ([string]::IsNullOrWhiteSpace($p)) { continue }
    if ($c -eq $p) { return $true }
    if ($p.StartsWith($c + '\')) { return $true }
    if ($c.StartsWith($p + '\')) { return $true }
  }
  return $false
}

function Get-VersionFromFolderName([string]$Name) {
  if ($Name -match '^KakaoEmoticonProfitSystemV([0-9]+)(?:_install_logs)?$') { return [int]$Matches[1] }
  if ($Name -match '^KakaoEmoticonV([0-9]+)$') { return [int]$Matches[1] }
  if ($Name -match '^kakao_emoticon_profit_system_v([0-9]+).*') { return [int]$Matches[1] }
  if ($Name -match '^Kakao_Emoticon_Profit_System_v([0-9]+).*') { return [int]$Matches[1] }
  return $null
}

$script:protectSourceNorm = Clean-InputPath $ProtectSource
$script:protectTargetNorm = Clean-InputPath $ProtectTarget
$backupRoot = Join-Path $localAppData 'KakaoEmoticonProfitSystemUserData\old_version_cleanup_backups'
$script:backupRootNorm = Clean-InputPath $backupRoot
$reportRoot = Join-Path $backupRoot $timestamp
New-Item -ItemType Directory -Force -Path $reportRoot | Out-Null
$reportPath = Join-Path $reportRoot 'cleanup_report.txt'

function Write-Report([string]$Text) {
  $Text | Tee-Object -FilePath $reportPath -Append
}

Write-Report 'Kakao Emoticon v54 old install/extracted cleanup report'
Write-Report "Timestamp: $timestamp"
Write-Report "LOCALAPPDATA: $localAppData"
Write-Report "CurrentVersion: v$CurrentVersion"
Write-Report "ProtectSource: $protectSourceNorm"
Write-Report "ProtectTarget: $protectTargetNorm"
Write-Report ''

$rootCandidates = New-Object System.Collections.Generic.List[string]
function Add-Root([string]$PathText) {
  $full = Clean-InputPath $PathText
  if ([string]::IsNullOrWhiteSpace($full)) { return }
  if ((Test-Path -LiteralPath $full) -and (-not $rootCandidates.Contains($full))) { $rootCandidates.Add($full) }
}

Add-Root $localAppData
Add-Root 'C:\'
Add-Root ([Environment]::GetFolderPath('DesktopDirectory'))
Add-Root (Join-Path $env:USERPROFILE 'Desktop')
Add-Root (Join-Path $env:USERPROFILE 'OneDrive\Desktop')

$dirCandidates = @()
foreach ($root in $rootCandidates) {
  Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    $version = Get-VersionFromFolderName $_.Name
    if ($version -ne $null -and $version -lt $CurrentVersion) {
      if (-not (Is-ProtectedPath $_.FullName)) {
        $dirCandidates += [PSCustomObject]@{
          Kind='Directory'; Version=$version; Name=$_.Name; FullName=$_.FullName; IsLog=($_.Name -like '*_install_logs')
        }
      }
    }
  }
}
$dirCandidates = $dirCandidates | Sort-Object FullName -Unique

$desktopCandidates = New-Object System.Collections.Generic.List[string]
function Add-Desktop([string]$PathText) {
  $full = Clean-InputPath $PathText
  if ([string]::IsNullOrWhiteSpace($full)) { return }
  if ((Test-Path -LiteralPath $full) -and (-not $desktopCandidates.Contains($full))) { $desktopCandidates.Add($full) }
}
Add-Desktop ([Environment]::GetFolderPath('DesktopDirectory'))
Add-Desktop (Join-Path $env:USERPROFILE 'Desktop')
Add-Desktop (Join-Path $env:USERPROFILE 'OneDrive\Desktop')

$linkCandidates = @()
foreach ($desktop in $desktopCandidates) {
  Get-ChildItem -LiteralPath $desktop -File -Filter '*.lnk' -ErrorAction SilentlyContinue | ForEach-Object {
    $n = $_.BaseName
    $version = $null
    if ($n -match 'Kakao Emoticon Profit System v([0-9]+)') { $version = [int]$Matches[1] }
    elseif ($n -match 'KakaoEmoticonProfitSystemV([0-9]+)') { $version = [int]$Matches[1] }
    elseif ($n -match 'Kakao Emoticon v([0-9]+)') { $version = [int]$Matches[1] }
    if ($version -ne $null -and $version -lt $CurrentVersion) {
      $linkCandidates += [PSCustomObject]@{ Kind='Shortcut'; Version=$version; Name=$_.Name; FullName=$_.FullName }
    }
  }
}
$linkCandidates = $linkCandidates | Sort-Object FullName -Unique

Write-Report 'Cleanup candidates:'
if ($dirCandidates.Count -eq 0 -and $linkCandidates.Count -eq 0) {
  Write-Report '- No old version folders or desktop shortcuts found.'
  Write-Host '[v54] No old versions found.'
  Write-Host "[v54] Report: $reportPath"
  exit 0
}
foreach ($c in $dirCandidates | Sort-Object Version, Name) { Write-Report "- DIR v$($c.Version): $($c.FullName)" }
foreach ($c in $linkCandidates | Sort-Object Version, Name) { Write-Report "- LNK v$($c.Version): $($c.FullName)" }
Write-Report ''

Write-Host ''
Write-Host '[v54] Cleanup candidates found:'
foreach ($c in $dirCandidates | Sort-Object Version, Name) { Write-Host "  [DIR] v$($c.Version) $($c.FullName)" }
foreach ($c in $linkCandidates | Sort-Object Version, Name) { Write-Host "  [LNK] v$($c.Version) $($c.FullName)" }
Write-Host ''
Write-Host '[v54] Only old Kakao Emoticon program folders/shortcuts are targeted.'
Write-Host '[v54] Documents, Downloads, Pictures, and unrelated personal folders are not targeted.'
Write-Host "[v54] Report path: $reportPath"

if ($Mode -eq 'ReportOnly') {
  Write-Report 'Mode=ReportOnly. No files deleted.'
  Write-Host '[v54] ReportOnly mode. No files deleted.'
  exit 0
}

$dataDirNames = @('outputs','user_data','settings','performance_data','strategy_reports','system_profile','reports','projects','backups','data','database','databases','migrated_old_outputs')
$dataFilePatterns = @('*.db','*.sqlite','*.sqlite3','*.csv','*.xlsx','*.xls','*.json','*.txt','*.md')
$backupMade = @()

foreach ($c in $dirCandidates | Where-Object { -not $_.IsLog }) {
  $srcDir = $c.FullName
  if (-not (Test-Path -LiteralPath $srcDir)) { continue }
  $safeName = ($c.Name -replace '[^a-zA-Z0-9_-]','_')
  $staging = Join-Path $reportRoot ("preserved_user_data_v$($c.Version)_$safeName")
  New-Item -ItemType Directory -Force -Path $staging | Out-Null
  $copiedAny = $false

  foreach ($dn in $dataDirNames) {
    $p = Join-Path $srcDir $dn
    if (Test-Path -LiteralPath $p) {
      $dest = Join-Path $staging $dn
      try {
        Copy-Item -LiteralPath $p -Destination $dest -Recurse -Force -ErrorAction Stop
        $copiedAny = $true
        Write-Report "Backed data dir: $p"
      } catch { Write-Report "[WARN] Failed to back up data dir $p : $($_.Exception.Message)" }
    }
  }

  foreach ($pat in $dataFilePatterns) {
    Get-ChildItem -LiteralPath $srcDir -File -Filter $pat -ErrorAction SilentlyContinue | ForEach-Object {
      try {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $staging $_.Name) -Force -ErrorAction Stop
        $copiedAny = $true
        Write-Report "Backed data file: $($_.FullName)"
      } catch { Write-Report "[WARN] Failed to back up data file $($_.FullName) : $($_.Exception.Message)" }
    }
  }

  if ($copiedAny) {
    $zipPath = Join-Path $reportRoot ("preserved_user_data_v$($c.Version)_$timestamp.zip")
    try {
      Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $zipPath -Force -ErrorAction Stop
      $backupMade += $zipPath
      Write-Report "User data backup ZIP: $zipPath"
      Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
    } catch {
      Write-Report "[WARN] Failed to create backup zip for $srcDir : $($_.Exception.Message)"
      Write-Report "Staging folder kept: $staging"
    }
  } else {
    Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
    Write-Report "No user data detected in: $srcDir"
  }
}

foreach ($c in $linkCandidates) {
  try {
    if (Test-Path -LiteralPath $c.FullName) {
      Remove-Item -LiteralPath $c.FullName -Force -ErrorAction Stop
      Write-Report "Removed shortcut: $($c.FullName)"
    }
  } catch { Write-Report "[WARN] Failed to remove shortcut $($c.FullName) : $($_.Exception.Message)" }
}

foreach ($c in $dirCandidates) {
  try {
    if (Test-Path -LiteralPath $c.FullName) {
      Remove-Item -LiteralPath $c.FullName -Recurse -Force -ErrorAction Stop
      Write-Report "Removed old directory: $($c.FullName)"
    }
  } catch { Write-Report "[WARN] Failed to remove directory $($c.FullName) : $($_.Exception.Message)" }
}

Write-Report ''
Write-Report 'Cleanup completed.'
if ($backupMade.Count -gt 0) {
  Write-Report 'Created backup ZIP files:'
  foreach ($b in $backupMade) { Write-Report "- $b" }
}
Write-Host "[v54] Cleanup completed. Report: $reportPath"
exit 0
