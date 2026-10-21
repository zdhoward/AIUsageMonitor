<#
.SYNOPSIS
  Manage the aimon monitoring service.
.EXAMPLE
  .\scripts\service.ps1 start       # start in the background (no console window)
  .\scripts\service.ps1 stop
  .\scripts\service.ps1 restart
  .\scripts\service.ps1 status      # health JSON from http://127.0.0.1:8797/healthz
  .\scripts\service.ps1 install     # start automatically at logon (per-user scheduled task)
  .\scripts\service.ps1 uninstall   # remove the logon task
#>
param([ValidateSet('start', 'stop', 'restart', 'status', 'install', 'uninstall')][string]$Action = 'status')
$ErrorActionPreference = 'Stop'
$serviceDir = Resolve-Path "$PSScriptRoot\..\service"
$taskName = 'AI Usage Monitor (aimon)'

function Find-Pythonw {
  $py = (Get-Command python -ErrorAction Stop).Source
  $pyw = Join-Path (Split-Path $py) 'pythonw.exe'
  if (Test-Path $pyw) { return $pyw }
  return $py
}

function Get-AimonProcess {
  Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
    Where-Object { $_.CommandLine -match '-m aimon' }
}

function Start-Aimon {
  if (Get-AimonProcess) { Write-Host 'aimon already running'; return }
  Start-Process -FilePath (Find-Pythonw) -ArgumentList '-m', 'aimon' -WorkingDirectory $serviceDir -WindowStyle Hidden
  Write-Host 'aimon started; logs in logs\aimon.log'
}

function Stop-Aimon {
  $procs = @(Get-AimonProcess)
  foreach ($p in $procs) { Stop-Process -Id $p.ProcessId -Force -Confirm:$false }
  Write-Host "stopped $($procs.Count) aimon process(es)"
}

switch ($Action) {
  'start' { Start-Aimon }
  'stop' { Stop-Aimon }
  'restart' { Stop-Aimon; Start-Sleep -Seconds 1; Start-Aimon }
  'status' {
    try { Invoke-RestMethod http://127.0.0.1:8797/healthz -TimeoutSec 3 | ConvertTo-Json -Depth 4 }
    catch { Write-Host 'aimon not reachable on 127.0.0.1:8797' }
  }
  'install' {
    $taskAction = New-ScheduledTaskAction -Execute (Find-Pythonw) -Argument '-m aimon' -WorkingDirectory $serviceDir
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
      -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    Register-ScheduledTask -TaskName $taskName -Action $taskAction -Trigger $trigger -Settings $settings `
      -Description 'Local AI usage monitor feeding the ESP32 display (S:\ZX\Programming\AIUsageMonitor)' -Force | Out-Null
    Write-Host "registered logon task '$taskName'"
  }
  'uninstall' {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "removed logon task '$taskName'"
  }
}
