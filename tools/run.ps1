<#
  run.ps1: the one command. It checks the data, regenerates the project files, then builds and launches the game with
  Igor. Nothing it starts opens a console window of its own; the only window you see is the game.

  Usage, from anywhere:
      powershell -NoProfile -ExecutionPolicy Bypass -File "<repo>\tools\run.ps1"
  or double click tools\run.vbs, which runs this script with no console at all.

  Exit codes:
      0  the game launched
      1  a data or project check failed (the game was NOT built)
      2  GameMaker is not installed, or Igor is there but no licence folder exists yet
      3  Igor ran and returned an error (the last 20 lines are printed)

  Status: VERIFIED 2026-10-20. GameMaker LTS2026 is installed on this PC: runtime-2026.0.0.23, Igor shipping inside the
  runtime at bin\igor\windows\x64\Igor.exe, and the account folder at %APPDATA%\GameMakerStudio2-LTS2026. Those folder
  names are not the 2024 ones this script was first written against, so the discovery below matches both lines.
  -Compile builds and stops; -SkipChecks skips the Python gates.
#>

[CmdletBinding()]
param(
    [switch]$SkipChecks,
    [switch]$Compile
)

$ErrorActionPreference = 'Stop'
$root  = Split-Path -Parent $PSScriptRoot
$game  = Join-Path $root 'game'
$yyp   = Join-Path $game 'PrimordialParadox.yyp'
$build = Join-Path $root 'build'
$log   = Join-Path $build 'last-build.log'
$igorLog = Join-Path $build 'last-igor.log'

New-Item -ItemType Directory -Force -Path $build | Out-Null
if (Test-Path $log) { Remove-Item $log -Force }
if (Test-Path $igorLog) { Remove-Item $igorLog -Force }

function Say([string]$message) {
    Write-Host $message
    Add-Content -Path $log -Value $message
}

function Fail([int]$code, [string]$message) {
    Say $message
    exit $code
}

# ---------------------------------------------------------------------------------------------------------------
# 1. Data and project checks. These are the gates that do not need GameMaker, so a broken data file stops here with a
#    readable message instead of a mystery at runtime.

$python = $null
foreach ($candidate in @('python', 'py')) {
    $found = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($null -ne $found) { $python = $found.Source; break }
}
if ($null -eq $python) { Fail 1 'Python is not on PATH, so the data checks cannot run. Install Python or run the checks by hand.' }

if (-not $SkipChecks) {
    foreach ($script in @('sync_data.py', 'sync_art.py', 'check_data.py', 'gen_project.py', 'check_project.py', 'check_cleanroom.py', 'check_provenance.py')) {
        $path = Join-Path $root "tools\$script"
        Say "running $script"
        $output = & $python $path 2>&1
        $code = $LASTEXITCODE
        foreach ($line in $output) { Add-Content -Path $log -Value $line }
        if ($code -ne 0) {
            foreach ($line in $output) { Write-Host $line }
            Fail 1 "$script failed (exit $code). The game was not built. Full log: $log"
        }
    }
}

# ---------------------------------------------------------------------------------------------------------------
# 2. Find the runtime, Igor and the licence folder.

$runtime = $env:PP_RUNTIME
if ([string]::IsNullOrWhiteSpace($runtime)) {
    # Two folder names exist in the wild: "GameMakerStudio2" for the 2024 line and "GameMakerStudio2-LTS2026" for the LTS
    # line installed here. Match either, and take the newest runtime by name.
    $runtimes = @()
    foreach ($wildcard in @('GameMakerStudio2', 'GameMakerStudio2-*')) {
        $productRoots = Get-ChildItem -Path $env:ProgramData -Directory -Filter $wildcard -ErrorAction SilentlyContinue
        foreach ($product in $productRoots) {
            $runtimeRoot = Join-Path $product.FullName 'Cache\runtimes'
            if (Test-Path $runtimeRoot) {
                $runtimes += Get-ChildItem -Path $runtimeRoot -Directory -Filter 'runtime-*' -ErrorAction SilentlyContinue
            }
        }
    }
    if ($runtimes.Count -gt 0) {
        $runtime = $runtimes | Sort-Object Name -Descending | Select-Object -First 1 -ExpandProperty FullName
    }
}
if ([string]::IsNullOrWhiteSpace($runtime)) {
    Fail 2 'GameMaker Studio is not installed on this PC (no runtime folder), so there is nothing to build yet. Install it and log in once, then run this again.'
}
if (-not (Test-Path $runtime)) { Fail 2 "PP_RUNTIME points at $runtime, which does not exist." }

$igor = $null
foreach ($relative in @('bin\igor\windows\x64\Igor.exe', 'bin\igor\windows\x86\Igor.exe', 'bin\igor\windows\Igor.exe')) {
    $candidate = Join-Path $runtime $relative
    if (Test-Path $candidate) { $igor = $candidate; break }
}
if ($null -eq $igor) { Fail 2 "The runtime at $runtime has no Igor.exe, so the command line build cannot run. Open GameMaker once and let it finish installing the runtime." }

$userFolder = $null
foreach ($wildcard in @('GameMakerStudio2', 'GameMakerStudio2-*')) {
    if ($null -ne $userFolder) { break }
    $productRoots = Get-ChildItem -Path $env:APPDATA -Directory -Filter $wildcard -ErrorAction SilentlyContinue
    foreach ($product in $productRoots) {
        # A named account lives in a subfolder ending in _<digits>. That is the folder the 2024 line wants.
        $account = Get-ChildItem -Path $product.FullName -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '_\d+$' } |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if ($null -ne $account) { $userFolder = $account.FullName; break }
        # The LTS line keeps um.json in the product folder itself and takes that folder as the user folder. Only trust
        # this for the '-suffix' product folder, never for the 2024 one, where a missing account must still stop the build.
        if ($product.Name -ne 'GameMakerStudio2' -and (Test-Path (Join-Path $product.FullName 'um.json'))) {
            $userFolder = $product.FullName
            break
        }
    }
}
if ([string]::IsNullOrWhiteSpace($userFolder)) {
    Fail 2 'Igor needs a licence folder and there is none yet. Open GameMaker Studio once, log in, then run this again. (That login is your step, not the bot''s.)'
}

if (-not (Test-Path $yyp)) { Fail 1 "The project file is missing: $yyp" }

# ---------------------------------------------------------------------------------------------------------------
# 3. Build and run.

$mode = 'Run'
if ($Compile) { $mode = 'Compile' }

# The flag forms below are the ones measured working against runtime-2026.0.0.23 on 2026-10-20. /cache and /temp are
# deliberately not passed: they were never proven on this runtime, and an unproven flag here would fail the build in a way
# that reads as the project being broken.
$arguments = @(
    "--project=`"$yyp`"",
    "--runtimePath=`"$runtime`"",
    "--uf=`"$userFolder`"",
    '--config=Default',
    '--', 'Windows', $mode
)

Say "building with $igor"
Say "game: $yyp"
Say "gate log:  $log"
Say "build log: $igorLog"

# Igor writes to its own file. Redirecting it onto the gate log would truncate the check output a user needs most when
# a build fails, and Start-Process truncates a redirect target.
#
# -WorkingDirectory is not optional. Igor resolves its cache and temp folders against the CURRENT directory, not
# against the project, so run from anywhere else it tries to create them under that folder and stops with
# "UnauthorizedAccessException: Access to the path '<current folder>\cache\PrimordialParadox' is denied" (measured
# 2026-10-20). The project root is the folder that holds the cache and output folders the build writes into.
$process = Start-Process -FilePath $igor -ArgumentList $arguments -WorkingDirectory $root -NoNewWindow -PassThru -Wait `
    -RedirectStandardOutput $igorLog -RedirectStandardError (Join-Path $build 'last-build-error.log')

if ($process.ExitCode -ne 0) {
    $tail = Get-Content -Path $igorLog -Tail 20 -ErrorAction SilentlyContinue
    foreach ($line in $tail) { Write-Host $line }
    Fail 3 "Igor returned $($process.ExitCode). The last 20 lines are above. Build log: $igorLog. Gate log: $log"
}

Say 'Igor finished. The game window is the only window that opened.'
exit 0
