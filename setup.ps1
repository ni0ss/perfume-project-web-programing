$ErrorActionPreference = 'Stop'
$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker is not installed. Install Docker Desktop for Windows, start it, and run this script again.'
}

docker compose version *> $null
if ($LASTEXITCODE -ne 0) {
    throw 'Docker Compose is unavailable. Install or update Docker Desktop, then retry.'
}

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw 'Docker Engine is not running. Start Docker Desktop, wait until it is ready, and retry.'
}

Write-Host 'Starting the perfume store and local Ollama models.'
Write-Host 'On first setup, Docker images and missing models are downloaded; internet is required.'

docker compose up --build -d
if ($LASTEXITCODE -ne 0) {
    docker compose ps -a
    docker compose logs --tail 80 ollama ollama-models web
    throw 'Docker Compose could not complete startup. See the service status and logs above.'
}

$ModelContainer = ''
while (-not $ModelContainer) {
    $ModelContainerResult = docker compose ps -aq ollama-models | Select-Object -First 1
    if ($ModelContainerResult) { $ModelContainer = $ModelContainerResult.Trim() }
    if (-not $ModelContainer) { Start-Sleep -Seconds 2 }
}

$Elapsed = 0
while ($true) {
    $ModelState = docker inspect --format '{{.State.Status}}|{{.State.ExitCode}}' $ModelContainer
    if ($LASTEXITCODE -ne 0) { throw 'Could not read the Ollama model setup status.' }
    if ($ModelState -eq 'exited|0') { break }
    if ($ModelState -like 'exited|*' -or $ModelState -like 'dead|*') {
        docker compose logs --tail 80 ollama-models
        throw 'Ollama model download/setup failed.'
    }
    Start-Sleep -Seconds 5
    $Elapsed += 5
    if ($Elapsed -ge 60) {
        Write-Host "Still preparing the models ($Elapsed seconds elapsed)..."
        $Elapsed = 0
    }
}

$RunningServices = docker compose ps --status running --services
if ($LASTEXITCODE -ne 0 -or $RunningServices -notcontains 'web') {
    docker compose ps -a
    docker compose logs --tail 80 ollama ollama-models web
    throw 'The web service is not running. Model download may have failed or still be in progress.'
}

Write-Host ''
Write-Host 'Setup complete.'
Write-Host 'Store:       http://localhost:8000/en/'
Write-Host 'Arabic page: http://localhost:8000/ar/'
Write-Host ''
Write-Host 'Installed Ollama models:'
docker compose exec -T ollama ollama list
Start-Process 'http://localhost:8000/en/'
