<#
.SYNOPSIS
  Compile the firmware for the ESP32-2432S024C with arduino-cli.
.EXAMPLE
  .\scripts\build.ps1                 # rotation from config.h (default 2)
  .\scripts\build.ps1 -Rotation 1     # override for a test build
#>
param(
  [ValidateSet(-1, 0, 1, 2, 3)][int]$Rotation = -1,
  [string]$OutDir = "$PSScriptRoot\..\build"
)
$ErrorActionPreference = 'Stop'
$cli = Join-Path $env:LOCALAPPDATA 'Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe'
if (-not (Test-Path $cli)) { $cli = (Get-Command arduino-cli -ErrorAction Stop).Source }
$sketch = Resolve-Path "$PSScriptRoot\..\firmware\AIUsageMonitor"

# TFT_eSPI setup for this board, identical to the User_Setup.h used by earlier
# sketches, passed as flags so the shared library file is never edited.
$tft = @(
  '-DUSER_SETUP_LOADED=1', '-DILI9341_DRIVER=1',
  '-DTFT_MISO=12', '-DTFT_MOSI=13', '-DTFT_SCLK=14', '-DTFT_CS=15', '-DTFT_DC=2', '-DTFT_RST=-1',
  '-DTFT_BL=27', '-DTFT_BACKLIGHT_ON=HIGH',
  '-DSPI_FREQUENCY=40000000', '-DSPI_READ_FREQUENCY=20000000', '-DSPI_TOUCH_FREQUENCY=2500000',
  '-DLOAD_GLCD=1', '-DLOAD_FONT2=1', '-DLOAD_FONT4=1', '-DSMOOTH_FONT=1'
)
if ($Rotation -ge 0) { $tft += "-DDISPLAY_ROTATION=$Rotation" }
$flags = $tft -join ' '

$ErrorActionPreference = 'Continue'  # native tools write progress to stderr
& $cli compile --fqbn esp32:esp32:esp32:FlashSize=4M,PartitionScheme=default `
  --build-property "compiler.cpp.extra_flags=$flags" `
  --build-property "compiler.c.extra_flags=$flags" `
  --output-dir $OutDir --warnings default $sketch
if ($LASTEXITCODE -ne 0) { throw "compile failed ($LASTEXITCODE)" }
Write-Host "build ok -> $OutDir"
