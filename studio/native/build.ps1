<#
.SYNOPSIS
  Build scenehost.dll (the firmware scene engine for Scene Studio's preview)
  with MSVC. Run after scripts/asset_convert.py so scenes_gen.cpp is current.
  Writes studio/native/build/scenehost-<stamp>.dll; the Studio loads the newest
  one, so a running Studio never blocks a rebuild.
#>
$ErrorActionPreference = 'Stop'
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$vs = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'MSVC (VC tools x64) not found' }
$fw = Resolve-Path "$PSScriptRoot\..\..\firmware\AIUsageMonitor"
$out = New-Item -ItemType Directory -Force "$PSScriptRoot\build"
$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$dll = Join-Path $out "scenehost-$stamp.dll"
$src = @("$PSScriptRoot\scenehost.cpp", "$fw\scene.cpp", "$fw\anim.cpp", "$fw\tune.cpp", "$fw\scenes_gen.cpp") -join '" "'
$cmd = "`"$vs\VC\Auxiliary\Build\vcvars64.bat`" >nul && cl /nologo /O2 /LD /EHsc /std:c++17 /utf-8 /W1 /I`"$fw`" /Fo`"$out\\`" /Fe`"$dll`" `"$src`""
cmd /c $cmd
if ($LASTEXITCODE -ne 0) { throw "native build failed ($LASTEXITCODE)" }
# keep the newest three builds; older ones may still be loaded by a running Studio
Get-ChildItem $out -Filter 'scenehost-*.dll' | Sort-Object Name -Descending | Select-Object -Skip 3 |
  ForEach-Object { Remove-Item $_.FullName -ErrorAction SilentlyContinue }
Write-Host "native ok -> $dll"
