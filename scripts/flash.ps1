<#
.SYNOPSIS
  Upload the last build to the display. Asks a running aimon service to release
  the COM port first, and lets it reconnect afterwards.
.EXAMPLE
  .\scripts\flash.ps1               # auto-detect the CH340 port
  .\scripts\flash.ps1 -Port COM6
#>
param([string]$Port = '', [string]$BuildDir = "$PSScriptRoot\..\build")
$ErrorActionPreference = 'Stop'

if (-not $Port) {
  $dev = Get-PnpDevice -PresentOnly -Class Ports | Where-Object { $_.InstanceId -match 'VID_1A86&PID_7523' } | Select-Object -First 1
  if (-not $dev) { throw 'No CH340 serial port found. Is the display plugged in?' }
  $Port = [regex]::Match($dev.FriendlyName, 'COM\d+').Value
}
$bin = Join-Path $BuildDir 'AIUsageMonitor.ino.merged.bin'
if (-not (Test-Path $bin)) { throw "No build at $bin. Run scripts\build.ps1 first." }

$paused = $false
try {
  Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8797/v1/serial/pause?seconds=180' -TimeoutSec 3 | Out-Null
  $paused = $true
  Start-Sleep -Milliseconds 800
  Write-Host 'aimon service released the port'
} catch { Write-Host 'aimon service not running (fine)' }

$esptool = Get-ChildItem "$env:LOCALAPPDATA\Arduino15\packages\esp32\tools\esptool_py" -Recurse -Filter esptool.exe |
  Sort-Object FullName -Descending | Select-Object -First 1
try {
  $ErrorActionPreference = 'Continue'  # native tools write progress to stderr
  & $esptool.FullName --chip esp32 --port $Port --baud 460800 write-flash 0x0 $bin
  if ($LASTEXITCODE -ne 0) { throw "upload failed ($LASTEXITCODE)" }
  Write-Host "flashed $bin to $Port"
} finally {
  if ($paused) {
    try { Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8797/v1/serial/resume' -TimeoutSec 3 | Out-Null } catch {}
  }
}
