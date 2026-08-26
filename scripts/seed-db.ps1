$ErrorActionPreference = "Stop"

$repoPath = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendPath = Join-Path $repoPath "python-backend"
$venvPython = Join-Path $repoPath ".venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }

Push-Location $backendPath
try {
    & $python -m app.cli seed-db
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
