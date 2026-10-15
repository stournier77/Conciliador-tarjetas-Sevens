$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Runtime = Join-Path $Root 'runtime_pc'
$UvDir = Join-Path $Runtime 'uv'
$Uv = Join-Path $UvDir 'uv.exe'
New-Item -ItemType Directory -Force -Path $UvDir,(Join-Path $Root 'logs') | Out-Null
$env:UV_CACHE_DIR = Join-Path $Runtime 'cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $Runtime 'python'
$env:UV_INSTALL_DIR = $UvDir
$env:UV_NO_MODIFY_PATH = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
Start-Transcript -Path (Join-Path $Root 'logs\ultimo_arranque_pc.log') -Append | Out-Null
try {
    if (-not (Test-Path $Uv)) {
        $script = Join-Path $Runtime 'install_uv.ps1'
        Invoke-WebRequest https://astral.sh/uv/install.ps1 -OutFile $script -TimeoutSec 45 -UseBasicParsing
        & $script
        Remove-Item $script
        if (-not (Test-Path $Uv)) { throw 'No se instaló uv.' }
    }
    $Python = (& $Uv python find --managed-python 3.12 2>$null)
    if ($LASTEXITCODE -ne 0) {
        & $Uv python install --no-bin --no-registry 3.12
        if ($LASTEXITCODE -ne 0) { throw 'No se instaló Python.' }
        $Python = (& $Uv python find --managed-python 3.12)
        if ($LASTEXITCODE -ne 0) { throw 'No se encontró Python.' }
    }
    $Python = ([string]$Python).Trim()
    & $Python (Join-Path $Root 'launchers\arranque.py') @args
    if ($LASTEXITCODE -ne 0) { throw 'Falló el inicio; revisá logs.' }
} catch { Write-Host $_; Read-Host 'Enter para cerrar'; exit 1 }
finally { Stop-Transcript | Out-Null }
