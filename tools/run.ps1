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

  Status: UNVERIFIED. As of 2026-10-19 there is no GameMaker install, runtime or licence on this PC, so this script
  has never reached step 4. Every path it looks for comes from knowledge\igor-cli.md.
#>

[CmdletBinding()]
param(
    [switch]$SkipChecks
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
    foreach ($script in @('sync_data.py', 'check_data.py', 'gen_project.py', 'check_project.py', 'check_cleanroom.py', 'check_provenance.py')) {
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
    $runtimeRoot = Join-Path $env:ProgramData 'GameMakerStudio2\Cache\runtimes'
    if (Test-Path $runtimeRoot) {
        $runtime = Get-ChildItem -Path $runtimeRoot -Directory -Filter 'runtime-*' -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            Select-Object -First 1 -ExpandProperty FullName
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
$userRoot = Join-Path $env:APPDATA 'GameMakerStudio2'
if (Test-Path $userRoot) {
    $userFolder = Get-ChildItem -Path $userRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '_\d+$' } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1 -ExpandProperty FullName
}
if ([string]::IsNullOrWhiteSpace($userFolder)) {
    Fail 2 'Igor needs a licence folder and there is none yet. Open GameMaker Studio once, log in, then run this again. (That login is your step, not the bot''s.)'
}

if (-not (Test-Path $yyp)) { Fail 1 "The project file is missing: $yyp" }

# ---------------------------------------------------------------------------------------------------------------
# 3. Build and run.

$cache = Join-Path $build 'cache'
$temp  = Join-Path $build 'temp'
New-Item -ItemType Directory -Force -Path $cache | Out-Null
New-Item -ItemType Directory -Force -Path $temp  | Out-Null

$arguments = @(
    "/project=`"$yyp`"",
    "/rp=`"$runtime`"",
    "/uf=`"$userFolder`"",
    "/cache=`"$cache`"",
    "/temp=`"$temp`"",
    '--', 'Windows', 'Run'
)

Say "building with $igor"
Say "game: $yyp"
Say "gate log:  $log"
Say "build log: $igorLog"

# Igor writes to its own file. Redirecting it onto the gate log would truncate the check output a user needs most when
# a build fails, and Start-Process truncates a redirect target.
$process = Start-Process -FilePath $igor -ArgumentList $arguments -NoNewWindow -PassThru -Wait `
    -RedirectStandardOutput $igorLog -RedirectStandardError (Join-Path $build 'last-build-error.log')

if ($process.ExitCode -ne 0) {
    $tail = Get-Content -Path $igorLog -Tail 20 -ErrorAction SilentlyContinue
    foreach ($line in $tail) { Write-Host $line }
    Fail 3 "Igor returned $($process.ExitCode). The last 20 lines are above. Build log: $igorLog. Gate log: $log"
}

Say 'Igor finished. The game window is the only window that opened.'
exit 0
