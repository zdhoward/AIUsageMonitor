<# Install/remove the headless, loopback-only CPAMC browser callback bridge. #>
[CmdletBinding()]
param([switch]$Install, [switch]$Remove)
$ErrorActionPreference = 'Stop'
if ($Install -and $Remove) { throw 'Choose Install or Remove.' }
$taskName = 'CPAMC Callback Bridge'
if ($Remove) {
  Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Output 'Removed CPAMC Callback Bridge.'
  exit 0
}
$pythonPath = (Get-Command python -ErrorAction Stop).Source
if ($pythonPath -match '\\WindowsApps\\') { throw 'Resolve a real Python interpreter before installing the bridge.' }
$bridgePath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'cpamc_callback_bridge.py')).ProviderPath
if ($pythonPath.Contains('"') -or $bridgePath.Contains('"')) { throw 'Unsupported quoted path.' }
$arguments = '--headless "' + $pythonPath + '" -B "' + $bridgePath + '"'
if (-not $Install) {
  Write-Output 'Preview: limited-user, headless CPAMC Callback Bridge at logon; loopback callbacks only.'
  Write-Output $arguments
  exit 0
}
$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\conhost.exe" -Argument $arguments -WorkingDirectory $PSScriptRoot
$logon = New-ScheduledTaskTrigger -AtLogOn -User $userId
$watchdog = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
  Stop-ScheduledTask -TaskName $taskName
  $deadline = (Get-Date).AddSeconds(10)
  while ((Get-ScheduledTask -TaskName $taskName).State -eq 'Running') {
    if ((Get-Date) -gt $deadline) { throw 'Existing callback bridge did not stop.' }
    Start-Sleep -Milliseconds 200
  }
}
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($logon, $watchdog) -Principal $principal -Settings $settings -Description 'Loopback-only Claude/Codex callback bridge to configured CPAMC; no management/API forwarding or credential storage.' -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Write-Output 'Installed and started CPAMC Callback Bridge.'
