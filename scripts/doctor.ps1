<#
.SYNOPSIS
  Quick safety check before or after a change: branch, remote, secrets, config, tools.
  Read-only. Exits 1 if any FAIL is found.
.PARAMETER Maintainer
  Allow working directly on main (for the project maintainer only).
.EXAMPLE
  .\scripts\doctor.ps1
#>
param([switch]$Maintainer)  # project maintainer: working on main is expected
$ErrorActionPreference = 'Continue'
Set-Location (Join-Path $PSScriptRoot '..')
$fail = 0
function Report($level, $msg) {
  $color = @{ OK = 'Green'; WARN = 'Yellow'; FAIL = 'Red' }[$level]
  Write-Host ("[{0}] {1}" -f $level, $msg) -ForegroundColor $color
  if ($level -eq 'FAIL') { $script:fail++ }
}

# Branch: customisations belong on my-setup, never on main.
$branch = (git rev-parse --abbrev-ref HEAD 2>$null)
if (-not $branch) { Report FAIL 'not inside a git repository' }
elseif ($branch -eq 'main' -and $Maintainer) { Report OK "branch: main (maintainer mode)" }
elseif ($branch -eq 'main') { Report FAIL "on 'main'. Run: git switch -c my-setup   (or git switch my-setup)" }
else { Report OK "branch: $branch" }

# main must match upstream so updates fast-forward.
git fetch origin --quiet 2>$null
$ahead = git rev-list --count origin/main..main 2>$null
if ($ahead -and [int]$ahead -gt 0) { Report FAIL "local main has $ahead commit(s) not in origin/main. Move them to my-setup before updating." }
elseif ($ahead -eq '0') { Report OK 'main matches origin/main (or is behind it)' }

# Uncommitted work.
$dirty = git status --porcelain 2>$null
if ($dirty) { Report WARN "uncommitted changes ($(@($dirty).Count) file(s)). Commit them on my-setup before updating." }
else { Report OK 'working tree clean' }

# Secrets must never be tracked.
$tracked = git ls-files -- 'service/aimon.config.json' 'firmware/AIUsageMonitor/secrets.h' 'service/.cpamc.env' 2>$null
if ($tracked) { Report FAIL "secret file is tracked by git: $($tracked -join ', ')" } else { Report OK 'no secret files tracked' }

# Config and ledger.
if (Test-Path 'service/aimon.config.json') { Report OK 'service/aimon.config.json exists' } else { Report WARN 'service/aimon.config.json missing (copy service/aimon.config.example.json)' }
if (Test-Path 'profiles/my.json') { Report OK 'personal profile profiles/my.json exists' } else { Report WARN 'no profiles/my.json (copy profiles/default.json to profiles/my.json and build with -Profile my)' }
if (Test-Path 'docs/MY_CHANGES.md') { Report OK 'docs/MY_CHANGES.md ledger exists' } else { Report WARN 'docs/MY_CHANGES.md missing (create it when you first edit a tracked file)' }

# Tools.
if (Get-Command python -ErrorAction SilentlyContinue) {
  Report OK ("python: " + (python --version 2>&1))
  python -c "import serial, tzdata, psutil" 2>$null
  if ($LASTEXITCODE -eq 0) { Report OK 'python packages: pyserial, tzdata, psutil' }
  else { Report WARN 'python packages missing. Run: python -m pip install -r service/requirements.txt' }
} else { Report FAIL 'python not found' }
$cli = Join-Path $env:LOCALAPPDATA 'Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe'
if ((Test-Path $cli) -or (Get-Command arduino-cli -ErrorAction SilentlyContinue)) { Report OK 'arduino-cli found' } else { Report WARN 'arduino-cli not found (needed to build firmware)' }

# Service.
try { Invoke-RestMethod -Uri 'http://127.0.0.1:8797/v1/status' -TimeoutSec 2 | Out-Null; Report OK 'service is running' }
catch { Report WARN 'service not running (.\scripts\service.ps1 start)' }

if ($fail) { Write-Host "`n$fail problem(s) need fixing." -ForegroundColor Red; exit 1 }
Write-Host "`nAll required checks passed." -ForegroundColor Green
