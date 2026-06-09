param(
  [int]$CurrentVersion = 46,
  [ValidateSet('Prompt','ReportOnly','AutoConfirm')]
  [string]$Mode = 'Prompt'
)

$ErrorActionPreference = 'Continue'
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$localAppData = $env:LOCALAPPDATA
if ([string]::IsNullOrWhiteSpace($localAppData) -or -not (Test-Path $localAppData)) {
  Write-Host '[ERROR] LOCALAPPDATA 경로를 찾을 수 없습니다.'
  exit 1
}

$backupRoot = Join-Path $localAppData 'KakaoEmoticonProfitSystemUserData\old_version_cleanup_backups'
$reportRoot = Join-Path $backupRoot $timestamp
New-Item -ItemType Directory -Force -Path $reportRoot | Out-Null
$reportPath = Join-Path $reportRoot 'cleanup_report.txt'

function Write-Report([string]$Text) {
  $Text | Tee-Object -FilePath $reportPath -Append
}

Write-Report 'Kakao Emoticon Profit System v46 old-version cleanup report'
Write-Report "Timestamp: $timestamp"
Write-Report "LOCALAPPDATA: $localAppData"
Write-Report "CurrentVersion: v$CurrentVersion"
Write-Report ''

# 설치 폴더 후보: LocalAppData 내부의 본 프로그램 버전 폴더만 대상으로 제한합니다.
$dirCandidates = @()
Get-ChildItem -Path $localAppData -Directory -ErrorAction SilentlyContinue | ForEach-Object {
  $name = $_.Name
  if ($name -match '^KakaoEmoticonProfitSystemV(\d+)(?:_install_logs)?$') {
    $version = [int]$Matches[1]
    if ($version -lt $CurrentVersion) {
      $dirCandidates += [PSCustomObject]@{
        Kind='Directory'; Version=$version; Name=$name; FullName=$_.FullName; IsLog=($name -like '*_install_logs')
      }
    }
  }
}

# 바탕화면 후보: 실제 Desktop, OneDrive Desktop, 기본 Desktop을 모두 검사합니다.
$desktopCandidates = New-Object System.Collections.Generic.List[string]
$desktop1 = [Environment]::GetFolderPath('DesktopDirectory')
if (-not [string]::IsNullOrWhiteSpace($desktop1)) { $desktopCandidates.Add($desktop1) }
$desktop2 = Join-Path $env:USERPROFILE 'OneDrive\Desktop'
$desktop3 = Join-Path $env:USERPROFILE 'Desktop'
foreach ($d in @($desktop2,$desktop3)) { if (-not $desktopCandidates.Contains($d)) { $desktopCandidates.Add($d) } }

$linkCandidates = @()
foreach ($desktop in $desktopCandidates) {
  if (Test-Path $desktop) {
    Get-ChildItem -Path $desktop -File -Filter '*.lnk' -ErrorAction SilentlyContinue | ForEach-Object {
      $n = $_.BaseName
      $version = $null
      if ($n -match 'Kakao Emoticon Profit System v(\d+)') { $version = [int]$Matches[1] }
      elseif ($n -match 'KakaoEmoticonProfitSystemV(\d+)') { $version = [int]$Matches[1] }
      elseif ($n -match '카카오.*이모티콘.*v(\d+)') { $version = [int]$Matches[1] }
      if ($version -ne $null -and $version -lt $CurrentVersion) {
        $linkCandidates += [PSCustomObject]@{
          Kind='Shortcut'; Version=$version; Name=$_.Name; FullName=$_.FullName
        }
      }
    }
  }
}

Write-Report 'Cleanup candidates:'
if ($dirCandidates.Count -eq 0 -and $linkCandidates.Count -eq 0) {
  Write-Report '- No old version install folders or desktop shortcuts found.'
  Write-Host '[v46] 정리할 이전 버전 폴더/바탕화면 아이콘이 없습니다.'
  Write-Host "[v46] 리포트: $reportPath"
  exit 0
}
foreach ($c in $dirCandidates | Sort-Object Version, Name) { Write-Report "- DIR v$($c.Version): $($c.FullName)" }
foreach ($c in $linkCandidates | Sort-Object Version, Name) { Write-Report "- LNK v$($c.Version): $($c.FullName)" }
Write-Report ''

Write-Host ''
Write-Host '[v46] 이전 버전 정리 후보를 찾았습니다.'
Write-Host '정리 대상은 LOCALAPPDATA 안의 KakaoEmoticonProfitSystemV이전버전 폴더와 바탕화면 바로가기만입니다.'
Write-Host '다운로드/문서/사진/개인 파일 전체 폴더는 건드리지 않습니다.'
Write-Host ''
foreach ($c in $dirCandidates | Sort-Object Version, Name) { Write-Host "  [폴더] v$($c.Version) $($c.FullName)" }
foreach ($c in $linkCandidates | Sort-Object Version, Name) { Write-Host "  [바로가기] v$($c.Version) $($c.FullName)" }
Write-Host ''

if ($Mode -eq 'ReportOnly') {
  Write-Report 'Mode=ReportOnly. No files were deleted.'
  Write-Host "[v46] 보고서만 생성했습니다. 삭제 없음: $reportPath"
  exit 0
}

if ($Mode -eq 'Prompt') {
  $answer = Read-Host '이전 버전 폴더/바로가기를 정리할까요? 사용자 데이터는 ZIP 백업 후 정리합니다. 계속하려면 Y 입력'
  if ($answer -ne 'Y' -and $answer -ne 'y') {
    Write-Report 'User declined cleanup. No files were deleted.'
    Write-Host '[v46] 이전 버전 정리를 건너뜁니다.'
    Write-Host "[v46] 리포트: $reportPath"
    exit 0
  }
}

# 사용자 데이터 후보만 백업합니다. 프로그램 코드 전체를 다시 백업하면 용량 절감 효과가 줄어들기 때문입니다.
$dataDirNames = @('outputs','user_data','settings','performance_data','strategy_reports','system_profile','reports','projects','backups','data','database','databases','migrated_old_outputs')
$dataFilePatterns = @('*.db','*.sqlite','*.sqlite3','*.csv','*.xlsx','*.xls','*.json','*.txt','*.md')
$backupMade = @()

foreach ($c in $dirCandidates | Where-Object { -not $_.IsLog }) {
  $srcDir = $c.FullName
  if (-not (Test-Path $srcDir)) { continue }
  $staging = Join-Path $reportRoot ("preserved_user_data_v$($c.Version)_" + ($c.Name -replace '[^a-zA-Z0-9_-]','_'))
  New-Item -ItemType Directory -Force -Path $staging | Out-Null
  $copiedAny = $false

  foreach ($dn in $dataDirNames) {
    $p = Join-Path $srcDir $dn
    if (Test-Path $p) {
      $dest = Join-Path $staging $dn
      try {
        Copy-Item -Path $p -Destination $dest -Recurse -Force -ErrorAction Stop
        $copiedAny = $true
        Write-Report "Backed data dir: $p"
      } catch {
        Write-Report "[WARN] Failed to back up data dir $p : $($_.Exception.Message)"
      }
    }
  }

  foreach ($pat in $dataFilePatterns) {
    Get-ChildItem -Path $srcDir -File -Filter $pat -ErrorAction SilentlyContinue | ForEach-Object {
      try {
        Copy-Item -Path $_.FullName -Destination (Join-Path $staging $_.Name) -Force -ErrorAction Stop
        $copiedAny = $true
        Write-Report "Backed data file: $($_.FullName)"
      } catch {
        Write-Report "[WARN] Failed to back up data file $($_.FullName) : $($_.Exception.Message)"
      }
    }
  }

  if ($copiedAny) {
    $zipPath = Join-Path $reportRoot ("preserved_user_data_v$($c.Version)_$timestamp.zip")
    try {
      Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $zipPath -Force -ErrorAction Stop
      $backupMade += $zipPath
      Write-Report "User data backup ZIP: $zipPath"
      Remove-Item -Path $staging -Recurse -Force -ErrorAction SilentlyContinue
    } catch {
      Write-Report "[WARN] Failed to create user data backup zip for $srcDir : $($_.Exception.Message)"
      Write-Report "Staging folder kept: $staging"
    }
  } else {
    Remove-Item -Path $staging -Recurse -Force -ErrorAction SilentlyContinue
    Write-Report "No user data folders/files detected in: $srcDir"
  }
}

# 삭제는 제한된 후보만 수행합니다.
foreach ($c in $linkCandidates) {
  try {
    if (Test-Path $c.FullName) {
      Remove-Item -Path $c.FullName -Force -ErrorAction Stop
      Write-Report "Removed shortcut: $($c.FullName)"
    }
  } catch {
    Write-Report "[WARN] Failed to remove shortcut $($c.FullName) : $($_.Exception.Message)"
  }
}

foreach ($c in $dirCandidates) {
  try {
    if (Test-Path $c.FullName) {
      Remove-Item -Path $c.FullName -Recurse -Force -ErrorAction Stop
      Write-Report "Removed old directory: $($c.FullName)"
    }
  } catch {
    Write-Report "[WARN] Failed to remove directory $($c.FullName) : $($_.Exception.Message)"
  }
}

Write-Report ''
Write-Report 'Cleanup completed.'
if ($backupMade.Count -gt 0) {
  Write-Report 'Created backup ZIP files:'
  foreach ($b in $backupMade) { Write-Report "- $b" }
}
Write-Host ''
Write-Host '[v46] 이전 버전 정리 완료.'
Write-Host "[v46] 백업/리포트 위치: $reportRoot"
exit 0
