<#
  capture_rect.ps1: capture one screen rectangle into a PNG with System.Drawing CopyFromScreen.

  This is the method that works on this PC for windows the computer-use screenshot tool returns blank for
  (see Shared\projects\arananet\manager\STATE.md). It is called by tools\capture_title.py, which finds the
  rectangle with user32 GetWindowRect.

  Usage:
      powershell -NoProfile -ExecutionPolicy Bypass -File capture_rect.ps1 -X 10 -Y 20 -W 300 -H 200 -Out C:\path\to.png
#>
param(
    [Parameter(Mandatory = $true)][int]$X,
    [Parameter(Mandatory = $true)][int]$Y,
    [Parameter(Mandatory = $true)][int]$W,
    [Parameter(Mandatory = $true)][int]$H,
    [Parameter(Mandatory = $true)][string]$Out
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

if ($W -le 0 -or $H -le 0) { Write-Error "bad rectangle ${W}x${H}"; exit 1 }

$bitmap = New-Object System.Drawing.Bitmap($W, $H)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
try {
    $graphics.CopyFromScreen($X, $Y, 0, 0, (New-Object System.Drawing.Size($W, $H)))
    $bitmap.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
}
finally {
    $graphics.Dispose()
    $bitmap.Dispose()
}
Write-Output "saved $Out ${W}x${H}"
exit 0
