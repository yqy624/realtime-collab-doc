param(
    [switch]$Yes
)

$ErrorActionPreference = "Stop"

$repoPath = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendPath = Join-Path $repoPath "python-backend"
$venvPython = Join-Path $repoPath ".venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }
$args = @("-m", "app.cli", "reset-db")
if ($Yes) {
    $args += "--yes"
}

Push-Location $backendPath
try {
    & $python @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
